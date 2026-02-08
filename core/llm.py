"""
SHERLOCK - LLM client for agents (Gemini via LangChain).
Agents use get_llm(); if None, they keep rule-based behavior.
"""

from typing import Any, Optional
from loguru import logger

from core.config import settings


_llm_cache: Optional[Any] = None


def get_llm():
    """Return a Gemini chat model if GEMINI_API_KEY is set; otherwise None."""
    global _llm_cache
    if _llm_cache is not None:
        return _llm_cache
    key = getattr(settings, "GEMINI_API_KEY", None)
    if not key or not str(key).strip():
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        model = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=key,
            temperature=getattr(settings, "LLM_TEMPERATURE", 0.1),
        )
        _llm_cache = llm
        logger.info(f"LLM loaded: Gemini {model}")
        return llm
    except Exception as e:
        logger.warning(f"Gemini LLM not available: {e}")
        return None
