"""
Claustor AI — Cross-Encoder Reranker
Reranks retrieved chunks by relevance to query.
Uses lightweight cross-encoder or sentence similarity fallback.
"""

from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


_cross_encoder = None

def _load_reranker():
    """Preload cross-encoder model — call once at startup."""
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder
            _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
            print("✅ Cross-encoder preloaded")
        except Exception as e:
            print(f"⚠️ Cross-encoder unavailable: {e}")
    return _cross_encoder


def rerank_chunks(query: str, chunks: list, top_k: int = 6) -> list:
    """
    Rerank chunks by relevance to query.
    Uses cross-encoder if available, else falls back to keyword overlap scoring.
    Returns top_k most relevant chunks.
    """
    if not chunks:
        return chunks

    if len(chunks) <= top_k:
        return chunks

    try:
        return _cross_encoder_rerank(query, chunks, top_k)
    except Exception as e:
        logger.warning(f"cross_encoder_unavailable: {e} — using keyword rerank")
        return _keyword_rerank(query, chunks, top_k)


def _cross_encoder_rerank(query: str, chunks: list, top_k: int) -> list:
    """
    Cross-encoder reranking using sentence-transformers.
    Uses cached model from _load_reranker() — never loads twice.
    """
    global _cross_encoder
    if _cross_encoder is None:
        _load_reranker()
    if _cross_encoder is None:
        raise RuntimeError("cross_encoder_not_available")
    model = _cross_encoder

    # Build pairs
    pairs = []
    for chunk in chunks:
        text = _get_chunk_text(chunk)
        pairs.append([query, text[:500]])

    scores = model.predict(pairs)

    # Sort by score
    scored = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    top = [chunk for _, chunk in scored[:top_k]]

    logger.info(f"cross_encoder_reranked: from={len(chunks)} to={len(top)} query={query[:40]!r}")
    return top


def _keyword_rerank(query: str, chunks: list, top_k: int) -> list:
    """
    Simple keyword overlap scoring as fallback reranker.
    Score = fraction of query terms found in chunk text.
    """
    import re
    query_terms = set(re.findall(r'\b\w{3,}\b', query.lower()))

    scored = []
    for chunk in chunks:
        text = _get_chunk_text(chunk).lower()
        chunk_terms = set(re.findall(r'\b\w{3,}\b', text))
        overlap = len(query_terms & chunk_terms)
        score = overlap / max(len(query_terms), 1)
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def _get_chunk_text(chunk: Any) -> str:
    """Extract text from chunk (dict or object)."""
    if isinstance(chunk, dict):
        return chunk.get("text", "") or chunk.get("content", "") or ""
    return getattr(chunk, "text", "") or getattr(chunk, "content", "") or str(chunk)
