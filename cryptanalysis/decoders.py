"""
SHERLOCK - Decode Base64, hex, ROT13.
"""

import re
import base64
import binascii
from typing import Optional, Tuple


def decode_base64(s: str) -> Optional[str]:
    try:
        s_clean = re.sub(r"\s+", "", s)
        raw = base64.b64decode(s_clean, validate=True)
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


def decode_hex(s: str) -> Optional[str]:
    try:
        s_clean = re.sub(r"[^0-9a-fA-F]", "", s)
        if len(s_clean) % 2:
            return None
        raw = binascii.unhexlify(s_clean)
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


def decode_rot13(s: str) -> str:
    return s.translate(str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
    ))


def decode_caesar(text: str, shift: int) -> str:
    """Decode Caesar cipher with given shift (0-25)."""
    out = []
    for c in text:
        if c.isupper():
            out.append(chr((ord(c) - ord("A") - shift) % 26 + ord("A")))
        elif c.islower():
            out.append(chr((ord(c) - ord("a") - shift) % 26 + ord("a")))
        else:
            out.append(c)
    return "".join(out)


def decode_vigenere(text: str, key: str) -> str:
    """Decode Vigenere with given key (letters only)."""
    key = "".join(c for c in key.lower() if c.isalpha())
    if not key:
        return text
    out = []
    ki = 0
    for c in text:
        if c.isupper():
            out.append(chr((ord(c) - ord("A") - (ord(key[ki % len(key)]) - ord("a"))) % 26 + ord("A")))
            ki += 1
        elif c.islower():
            out.append(chr((ord(c) - ord("a") - (ord(key[ki % len(key)]) - ord("a"))) % 26 + ord("a")))
            ki += 1
        else:
            out.append(c)
    return "".join(out)


def decode_segment(crypto_type: str, content: str, shift: Optional[int] = None) -> Optional[str]:
    if crypto_type == "base64":
        return decode_base64(content)
    if crypto_type == "hex":
        return decode_hex(content)
    if crypto_type == "rot13":
        return decode_rot13(content)
    if crypto_type == "caesar" and shift is not None:
        return decode_caesar(content, shift)
    return None
