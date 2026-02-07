"""
SHERLOCK - Frequency analysis for classical ciphers.
"""

from collections import Counter
from typing import Dict, List

# Reference letter frequencies (relative) for Portuguese and English
PT_FREQ = {
    "a": 0.1463, "e": 0.1257, "o": 0.1078, "s": 0.0781, "r": 0.0682,
    "i": 0.0618, "d": 0.0592, "n": 0.0569, "m": 0.0514, "t": 0.0512,
    "c": 0.0454, "u": 0.0362, "l": 0.0344, "p": 0.0315, "q": 0.0208,
    "v": 0.0162, "g": 0.0130, "h": 0.0128, "f": 0.0102, "b": 0.0104,
    "z": 0.0092, "x": 0.0032, "j": 0.0040, "k": 0.0002, "w": 0.0001, "y": 0.0064,
}
EN_FREQ = {
    "e": 0.1270, "t": 0.0906, "a": 0.0817, "o": 0.0751, "i": 0.0697,
    "n": 0.0675, "s": 0.0633, "h": 0.0609, "r": 0.0599, "d": 0.0425,
    "l": 0.0403, "c": 0.0278, "u": 0.0276, "m": 0.0241, "w": 0.0236,
    "f": 0.0223, "g": 0.0202, "y": 0.0197, "p": 0.0193, "b": 0.0129,
    "v": 0.0098, "k": 0.0077, "j": 0.0015, "x": 0.0015, "q": 0.0010, "z": 0.0007,
}


def char_frequency(text: str) -> Dict[str, float]:
    """Character frequency in [0,1] for letters only."""
    if not text:
        return {}
    c = Counter(c.lower() for c in text if c.isalpha())
    total = sum(c.values())
    return {k: v / total for k, v in c.most_common()} if total else {}


def _correlation(f1: Dict[str, float], f2: Dict[str, float]) -> float:
    """Correlation between two frequency dicts (over common keys)."""
    keys = set(f1) | set(f2)
    if not keys:
        return 0.0
    n = len(keys)
    v1 = [f1.get(k, 0) for k in keys]
    v2 = [f2.get(k, 0) for k in keys]
    m1 = sum(v1) / n
    m2 = sum(v2) / n
    num = sum((a - m1) * (b - m2) for a, b in zip(v1, v2))
    den1 = (sum((a - m1) ** 2 for a in v1) ** 0.5) or 1
    den2 = (sum((b - m2) ** 2 for b in v2) ** 0.5) or 1
    return num / (den1 * den2) if (den1 * den2) else 0


def suggest_caesar_shift(cipher_text: str, lang: str = "pt") -> int:
    """Suggest Caesar shift by correlating decrypted letter frequencies with language."""
    cipher_text = "".join(c for c in cipher_text if c.isalpha())
    if len(cipher_text) < 20:
        return 0
    lang_freq = EN_FREQ if lang == "en" else PT_FREQ
    best_shift, best_corr = 0, -1
    for shift in range(26):
        dec = []
        for c in cipher_text:
            if c.isupper():
                dec.append(chr((ord(c) - ord("A") - shift) % 26 + ord("A")))
            else:
                dec.append(chr((ord(c) - ord("a") - shift) % 26 + ord("a")))
        dec_freq = char_frequency("".join(dec))
        corr = _correlation(dec_freq, lang_freq)
        if corr > best_corr:
            best_corr = corr
            best_shift = shift
    return best_shift
