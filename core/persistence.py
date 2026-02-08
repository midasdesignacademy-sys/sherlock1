"""
SHERLOCK - SQLite ledger for document processing (resilience and resume).
Tracks per-document status per investigation so ingestion can skip DONE and retry FAILED.
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from core.config import settings

_LOCK = threading.Lock()
_CONN: Optional[sqlite3.Connection] = None

def _ledger_path() -> Path:
    return getattr(settings, "LEDGER_DB_PATH", None) or (settings.DATA_DIR / "processing_ledger.db")

STATUS_PENDING = "PENDING"
STATUS_PROCESSING = "PROCESSING"
STATUS_DONE = "DONE"
STATUS_FAILED = "FAILED"


def _get_conn() -> sqlite3.Connection:
    global _CONN
    with _LOCK:
        if _CONN is None:
            path = _ledger_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            _CONN = sqlite3.connect(str(path), check_same_thread=False)
            _CONN.execute(
                """
                CREATE TABLE IF NOT EXISTS doc_processing_ledger (
                    doc_hash TEXT NOT NULL,
                    investigation_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_agent_id TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (doc_hash, investigation_id)
                )
                """
            )
            _CONN.commit()
        return _CONN


def log_doc_start(doc_hash: str, investigation_id: str) -> None:
    """Mark document as PROCESSING. Upserts row."""
    inv = investigation_id or ""
    conn = _get_conn()
    now = datetime.utcnow().isoformat() + "Z"
    with _LOCK:
        conn.execute(
            """
            INSERT INTO doc_processing_ledger (doc_hash, investigation_id, status, last_agent_id, retry_count, updated_at)
            VALUES (?, ?, ?, ?, 0, ?)
            ON CONFLICT(doc_hash, investigation_id) DO UPDATE SET
                status = ?,
                last_agent_id = ?,
                updated_at = ?
            """,
            (doc_hash, inv, STATUS_PROCESSING, "ingest_documents", now, STATUS_PROCESSING, "ingest_documents", now),
        )
        conn.commit()


def log_doc_success(doc_hash: str, investigation_id: str) -> None:
    """Mark document as DONE."""
    inv = investigation_id or ""
    conn = _get_conn()
    now = datetime.utcnow().isoformat() + "Z"
    with _LOCK:
        conn.execute(
            """
            INSERT INTO doc_processing_ledger (doc_hash, investigation_id, status, last_agent_id, retry_count, updated_at)
            VALUES (?, ?, ?, ?, 0, ?)
            ON CONFLICT(doc_hash, investigation_id) DO UPDATE SET
                status = ?,
                last_agent_id = ?,
                updated_at = ?
            """,
            (doc_hash, inv, STATUS_DONE, "ingest_documents", now, STATUS_DONE, "ingest_documents", now),
        )
        conn.commit()


def log_doc_failed(doc_hash: str, investigation_id: str, last_agent_id: str = "ingest_documents") -> None:
    """Mark document as FAILED and increment retry_count."""
    inv = investigation_id or ""
    conn = _get_conn()
    now = datetime.utcnow().isoformat() + "Z"
    with _LOCK:
        conn.execute(
            """
            INSERT INTO doc_processing_ledger (doc_hash, investigation_id, status, last_agent_id, retry_count, updated_at)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(doc_hash, investigation_id) DO UPDATE SET
                status = ?,
                last_agent_id = ?,
                retry_count = retry_count + 1,
                updated_at = ?
            """,
            (doc_hash, inv, STATUS_FAILED, last_agent_id, now, STATUS_FAILED, last_agent_id, now),
        )
        conn.commit()


def get_doc_status(doc_hash: str, investigation_id: str) -> Optional[str]:
    """Return status for (doc_hash, investigation_id) or None if not in ledger."""
    inv = investigation_id or ""
    conn = _get_conn()
    with _LOCK:
        row = conn.execute(
            "SELECT status FROM doc_processing_ledger WHERE doc_hash = ? AND investigation_id = ?",
            (doc_hash, inv),
        ).fetchone()
    return row[0] if row else None


def get_pending_docs(
    investigation_id: str,
    max_retries: int = 5,
) -> List[Tuple[str, int]]:
    """Return list of (doc_hash, retry_count) for docs with status PENDING or FAILED and retry_count < max_retries."""
    inv = investigation_id or ""
    conn = _get_conn()
    with _LOCK:
        rows = conn.execute(
            """
            SELECT doc_hash, retry_count FROM doc_processing_ledger
            WHERE investigation_id = ? AND status IN (?, ?) AND retry_count < ?
            """,
            (inv, STATUS_PENDING, STATUS_FAILED, max_retries),
        ).fetchall()
    return [(r[0], r[1]) for r in rows]
