"""
SHERLOCK - Steganography detection (LSB in PNG via stegano).
"""

from pathlib import Path
from typing import List, Dict, Any


def detect_image_stego(file_path: Path) -> List[Dict[str, Any]]:
    """Detect LSB steganography in PNG; return list of findings."""
    findings: List[Dict[str, Any]] = []
    suf = file_path.suffix.lower()
    if suf != ".png":
        return [{"type": "image_check", "path": str(file_path), "note": "Stego check only for PNG"}]
    try:
        from stegano import lsb
        revealed = lsb.reveal(str(file_path))
        if revealed and revealed.strip():
            findings.append({
                "type": "lsb_revealed",
                "path": str(file_path),
                "content_preview": (revealed[:200] + "...") if len(revealed) > 200 else revealed,
            })
    except ImportError:
        findings.append({"type": "stego_check", "path": str(file_path), "note": "Install stegano for LSB detection"})
    except Exception as e:
        findings.append({"type": "stego_error", "path": str(file_path), "error": str(e)})
    return findings
