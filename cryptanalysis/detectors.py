"""
SHERLOCK - Detect encrypted/obfuscated segments (Base64, hex, ROT13, etc.).
"""

import re
import base64
import binascii
from typing import List, Tuple, Optional


def is_base64(s: str) -> bool:
    try:
        s_clean = re.sub(r"\s+", "", s)
        if len(s_clean) % 4:
            return False
        base64.b64decode(s_clean, validate=True)
        return True
    except Exception:
        return False


def is_hex(s: str) -> bool:
    s_clean = re.sub(r"[^0-9a-fA-F]", "", s)
    return len(s_clean) >= 8 and len(s_clean) % 2 == 0


def is_rot13(s: str) -> bool:
    if len(s) < 10:
        return False
    decoded = s.translate(str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
    ))
    return decoded != s and decoded.isprintable()


def detect_base64_blocks(text: str) -> List[Tuple[int, int, str]]:
    """Return list of (start, end, content) for likely Base64 blocks."""
    pattern = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")
    out = []
    for m in pattern.finditer(text):
        segment = m.group(0)
        if is_base64(segment):
            out.append((m.start(), m.end(), segment))
    return out


def detect_hex_blocks(text: str) -> List[Tuple[int, int, str]]:
    """Return list of (start, end, content) for likely hex blocks."""
    pattern = re.compile(r"\b(?:0x)?[0-9a-fA-F]{16,}\b")
    out = []
    for m in pattern.finditer(text):
        seg = re.sub(r"^0x", "", m.group(0))
        if len(seg) >= 16 and len(seg) % 2 == 0:
            out.append((m.start(), m.end(), m.group(0)))
    return out


def detect_caesar_blocks(text: str, min_len: int = 20) -> List[Tuple[int, int, str, int]]:
    """Return list of (start, end, content, suggested_shift). Blocks of letters only."""
    try:
        from cryptanalysis.frequency import suggest_caesar_shift
    except ImportError:
        return []
    pattern = re.compile(r"[A-Za-z\s]{%d,}" % min_len)
    out = []
    for m in pattern.finditer(text):
        content = m.group(0)
        letters_only = "".join(c for c in content if c.isalpha())
        if len(letters_only) < min_len:
            continue
        shift = suggest_caesar_shift(letters_only, "pt")
        out.append((m.start(), m.end(), content, shift))
    return out


def detect_all(text: str) -> List[Tuple[str, int, int, str, Optional[int]]]:
    """Return list of (crypto_type, start, end, content, optional_shift)."""
    found: List[Tuple[str, int, int, str, Optional[int]]] = []
    for start, end, content in detect_base64_blocks(text):
        found.append(("base64", start, end, content, None))
    for start, end, content in detect_hex_blocks(text):
        found.append(("hex", start, end, content, None))
    for start, end, content, shift in detect_caesar_blocks(text):
        found.append(("caesar", start, end, content, shift))
    return found
