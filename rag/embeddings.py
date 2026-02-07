"""
SHERLOCK - Embeddings (sentence-transformers).
"""

from typing import List
from loguru import logger

from core.config import settings


def get_embedding_model():
    """Load sentence-transformers model."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info(f"Loaded embedding model: {settings.EMBEDDING_MODEL}")
        return model
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        raise


def embed_texts(texts: List[str], model=None) -> List[List[float]]:
    """Embed a list of texts. Returns list of vectors."""
    if model is None:
        model = get_embedding_model()
    if not texts:
        return []
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


def embed_single(text: str, model=None) -> List[float]:
    """Embed a single text."""
    return embed_texts([text], model=model)[0]
