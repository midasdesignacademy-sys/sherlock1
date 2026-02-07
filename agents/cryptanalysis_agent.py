"""
SHERLOCK - Cryptanalysis Hunter Agent (Agent 4)
Soul: docs/agents/agent_4_soul.md
Detects/decodes encrypted/obfuscated content; outputs cryptography_findings (Soul contract).
"""

from typing import Dict, List, Any
from pathlib import Path
from loguru import logger

from core.state import InvestigationState, CryptoSegment
from cryptanalysis.detectors import detect_all
from cryptanalysis.decoders import decode_segment
from cryptanalysis.steganography import detect_image_stego


def _location_from_pos(text: str, start: int, end: int) -> str:
    """Approximate location (line/char) for Soul 'location' field."""
    line = text[:start].count("\n") + 1
    return f"char {start}-{end}, line ~{line}"


class CryptanalysisHunterAgent:
    """Agent 4: Scan for crypto; decode; fill encrypted_segments and cryptography_findings (Soul)."""

    def process(self, state: InvestigationState) -> InvestigationState:
        logger.info("[Agent 4] Cryptanalysis...")
        try:
            encrypted_segments = list(state.get("encrypted_segments", []))
            decrypted_content = dict(state.get("decrypted_content", {}))
            cryptography_findings: List[Dict[str, Any]] = list(state.get("cryptography_findings", []))
            extracted = state.get("extracted_text", {}) or {}

            seg_id = 0
            for doc_id, text in extracted.items():
                if not text:
                    continue
                for item in detect_all(text):
                    crypto_type = item[0]
                    start, end, content = item[1], item[2], item[3]
                    shift = item[4] if len(item) > 4 else None
                    seg_id += 1
                    sid = f"seg_{doc_id}_{seg_id}"
                    dec = decode_segment(crypto_type, content, shift=shift)
                    if dec:
                        decrypted_content[sid] = dec
                    enc = CryptoSegment(
                        segment_id=sid,
                        doc_id=doc_id,
                        content=content[:500],
                        start_pos=start,
                        end_pos=end,
                        crypto_type=crypto_type,
                        confidence=0.9,
                        decrypted_content=dec,
                    )
                    encrypted_segments.append(enc)
                    finding_type = "base64_encoded" if crypto_type == "base64" else f"{crypto_type}_encoded"
                    cryptography_findings.append({
                        "document_id": doc_id,
                        "finding_type": finding_type,
                        "location": _location_from_pos(text, start, end),
                        "encoded_text": content[:200] + ("..." if len(content) > 200 else ""),
                        "decoded_preview": (dec[:150] + "...") if dec and len(dec) > 150 else (dec or ""),
                        "confidence": 0.95 if dec else 0.7,
                        "algorithm": crypto_type,
                    })

            upload_path = state.get("config", {}).get("uploads_path")
            if upload_path:
                upload_dir = Path(upload_path)
                for ext in [".png", ".jpg", ".jpeg"]:
                    for img_path in upload_dir.glob(f"*{ext}"):
                        for finding in detect_image_stego(img_path):
                            seg_id += 1
                            sid = f"stego_{seg_id}"
                            encrypted_segments.append(CryptoSegment(
                                segment_id=sid,
                                doc_id="",
                                content=finding.get("content_preview", finding.get("note", ""))[:500],
                                start_pos=0,
                                end_pos=0,
                                crypto_type="stego",
                                confidence=0.8,
                                decrypted_content=finding.get("content_preview"),
                            ))
                            cryptography_findings.append({
                                "document_id": str(img_path),
                                "finding_type": "steganography",
                                "location": f"image {img_path.name}",
                                "encoded_text": None,
                                "decoded_preview": finding.get("content_preview", finding.get("note", "")),
                                "confidence": 0.8,
                                "algorithm": "lsb",
                            })

            state["encrypted_segments"] = encrypted_segments
            state["decrypted_content"] = decrypted_content
            state["cryptography_findings"] = cryptography_findings
            state["current_step"] = "cryptanalysis_complete"
            logger.info(f"[Agent 4] Segments: {len(encrypted_segments)}, Findings: {len(cryptography_findings)}")
        except Exception as e:
            logger.error(f"[Agent 4] Error: {e}")
            state["error_log"] = state.get("error_log", []) + [f"Cryptanalysis error: {str(e)}"]
        return state
