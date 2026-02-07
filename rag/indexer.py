"""
SHERLOCK - Document chunking and indexing into vector store.
"""

import re
from typing import List, Dict, Any
from loguru import logger

from rag.vector_store import get_chroma_client, get_or_create_collection, add_chunks
from rag.embeddings import get_embedding_model


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks (by characters)."""
    if not text or not text.strip():
        return []
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap if overlap < chunk_size else end
    return chunks


def chunk_by_paragraphs(text: str, max_chars: int = 800) -> List[str]:
    """Chunk by paragraphs, then by size."""
    paras = re.split(r"\n\s*\n", text)
    chunks = []
    current = []
    current_len = 0
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if current_len + len(p) + 2 > max_chars and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(p)
        current_len += len(p) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def index_documents_from_state(state: Dict[str, Any], collection=None, model=None) -> None:
    """Index extracted_text from state into Chroma. Uses chunk_by_paragraphs."""
    extracted = state.get("extracted_text", {})
    if not extracted:
        return
    if model is None:
        model = get_embedding_model()
    if collection is None:
        client = get_chroma_client()
        collection = get_or_create_collection(client)
    for doc_id, text in extracted.items():
        if not text or len(text.strip()) < 20:
            continue
        chunks = chunk_by_paragraphs(text, max_chars=600)
        if not chunks:
            chunks = chunk_text(text, chunk_size=400, overlap=40)
        if chunks:
            add_chunks(doc_id, chunks, model=model, collection=collection)
            logger.debug(f"Indexed {doc_id} ({len(chunks)} chunks)")
