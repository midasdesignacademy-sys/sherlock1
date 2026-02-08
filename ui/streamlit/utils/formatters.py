"""Formatters for display (dates, numbers)."""
from typing import Any


def format_entity_type(t: Any) -> str:
    return str(t) if t else "—"


def format_confidence(c: Any) -> str:
    try:
        return f"{float(c):.2f}" if c is not None else "—"
    except (TypeError, ValueError):
        return "—"
