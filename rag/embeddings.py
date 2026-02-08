"""
SHERLOCK - Embeddings: local (sentence-transformers) or OpenAI.
"""

from typing import List, Any, Optional
from loguru import logger

from core.config import settings

_embedding_model: Optional[Any] = None


def get_embedding_model():
    """Load embedding model: OpenAI if EMBEDDING_PROVIDER=openai and OPENAI_API_KEY set; else sentence-transformers."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    provider = getattr(settings, "EMBEDDING_PROVIDER", "local")
    if provider == "openai" and getattr(settings, "OPENAI_API_KEY", None):
        try:
            from langchain_openai import OpenAIEmbeddings
            model_name = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
            _embedding_model = OpenAIEmbeddings(
                model=model_name,
                openai_api_key=settings.OPENAI_API_KEY,
            )
            logger.info(f"Loaded OpenAI embedding model: {model_name}")
            return _embedding_model
        except Exception as e:
            logger.warning(f"OpenAI embeddings not available: {e}, falling back to local")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(settings.EMBEDDING_MODEL)
        _embedding_model = model
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
    if hasattr(model, "embed_documents"):
        emb = model.embed_documents(texts)
        return [[float(x) for x in vec] for vec in emb]
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


def embed_single(text: str, model=None) -> List[float]:
    """Embed a single text."""
    if model is None:
        model = get_embedding_model()
    if hasattr(model, "embed_query"):
        return [float(x) for x in model.embed_query(text)]
    return embed_texts([text], model=model)[0]
