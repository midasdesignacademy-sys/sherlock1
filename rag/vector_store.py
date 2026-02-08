"""
SHERLOCK - Vector store (Chroma).
"""

from typing import List, Optional, Dict, Any
from loguru import logger

from core.config import settings


def get_chroma_client():
    """Get Chroma client (persistent or in-memory)."""
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        # Prefer persistent; fallback to in-memory if no server
        try:
            client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
            )
            client.heartbeat()
            return client
        except Exception:
            client = chromadb.Client(ChromaSettings(anonymized_telemetry=False))
            logger.warning("Chroma server not available; using in-memory store")
            return client
    except ImportError:
        logger.error("chromadb not installed")
        raise


def get_or_create_collection(client=None, name: Optional[str] = None):
    """Get or create collection."""
    if client is None:
        client = get_chroma_client()
    coll_name = name or settings.CHROMA_COLLECTION
    return client.get_or_create_collection(name=coll_name, metadata={"description": "SHERLOCK documents"})


def add_chunks(
    doc_id: str,
    chunks: List[str],
    chunk_ids: Optional[List[str]] = None,
    embeddings: Optional[List[List[float]]] = None,
    model=None,
    collection=None,
) -> None:
    """Add document chunks to collection. If embeddings is None, compute them."""
    if collection is None:
        client = get_chroma_client()
        collection = get_or_create_collection(client)
    if not chunks:
        return
    if chunk_ids is None:
        chunk_ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    if embeddings is None:
        from rag.embeddings import embed_texts
        embeddings = embed_texts(chunks, model=model)
    collection.add(
        ids=chunk_ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=[{"doc_id": doc_id}] * len(chunks),
    )


def query_similar(
    text_or_embedding: Any,
    n_results: int = 10,
    doc_ids_filter: Optional[List[str]] = None,
    collection=None,
    model=None,
) -> List[Dict[str, Any]]:
    """Query by text (will be embedded) or by embedding vector. Returns list of {id, document, metadata, distance}."""
    if collection is None:
        client = get_chroma_client()
        collection = get_or_create_collection(client)
    if isinstance(text_or_embedding, str):
        from rag.embeddings import embed_single
        query_embedding = embed_single(text_or_embedding, model=model)
    else:
        query_embedding = text_or_embedding
    where = {"doc_id": {"$in": doc_ids_filter}} if doc_ids_filter else None
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    out = []
    for i, id_ in enumerate(result["ids"][0] or []):
        out.append({
            "id": id_,
            "document": (result["documents"][0] or [])[i] if result["documents"] else None,
            "metadata": (result["metadatas"][0] or [{}])[i] if result["metadatas"] else {},
            "distance": (result["distances"][0] or [0])[i] if result.get("distances") else None,
        })
    return out
