"""
Claustor AI — RAG Retriever
Orchestrates hybrid search + context building for the AI Copilot.
"""

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.vector_store.hybrid_search import (
    HybridSearchEngine, HybridSearchResult, get_hybrid_search,
)

logger = structlog.get_logger(__name__)

# Context window budget per plan
CONTEXT_LIMITS = {
    "free":         2000,   # 2K chars
    "starter":      4000,   # 4K chars
    "professional": 8000,   # 8K chars
    "enterprise":   16000,  # 16K chars
}

# Top-K results per plan
TOP_K_LIMITS = {
    "free":         2,
    "starter":      4,
    "professional": 6,
    "enterprise":   10,
}


class RetrievedContext:
    """Context retrieved for a query, ready to pass to LLM."""

    def __init__(
        self,
        chunks: list[HybridSearchResult],
        context_text: str,
        citations: list[dict],
        query: str,
    ):
        self.chunks = chunks
        self.context_text = context_text
        self.citations = citations
        self.query = query
        self.total_chars = len(context_text)

    def to_prompt_context(self) -> str:
        """Format context for LLM prompt."""
        return self.context_text


class RAGRetriever:
    """
    RAG retriever with hybrid search.
    Retrieves, deduplicates, and formats context for LLM.
    """

    def __init__(self):
        self.hybrid_engine: HybridSearchEngine = get_hybrid_search()

    async def retrieve(
        self,
        query: str,
        org_id: UUID,
        db: AsyncSession,
        plan: str = "starter",
        contract_id: UUID | None = None,
        clause_type: str | None = None,
    ) -> RetrievedContext:
        """
        Retrieve relevant context for a query.

        Args:
            query:       User's natural language query
            org_id:      Organisation (enforces data isolation)
            db:          DB session for keyword search
            plan:        User's plan (controls context size)
            contract_id: Optional — search within specific contract
            clause_type: Optional — filter by clause type

        Returns:
            RetrievedContext with formatted text + citations
        """
        top_k = TOP_K_LIMITS.get(plan, 4)
        context_limit = CONTEXT_LIMITS.get(plan, 4000)

        # Hybrid search
        chunks = await self.hybrid_engine.search(
            query=query,
            org_id=org_id,
            db=db,
            contract_id=contract_id,
            top_k=top_k,
            clause_type=clause_type,
        )

        if not chunks:
            logger.warning(
                "no_chunks_retrieved",
                query=query[:50],
                org_id=str(org_id),
                contract_id=str(contract_id) if contract_id else None,
            )
            return RetrievedContext(
                chunks=[],
                context_text="No relevant information found in the contract.",
                citations=[],
                query=query,
            )

        # Build context text with citations
        context_parts = []
        citations = []
        total_chars = 0

        for i, chunk in enumerate(chunks):
            chunk_text = chunk.text.strip()
            if not chunk_text:
                continue

            # Respect context limit
            if total_chars + len(chunk_text) > context_limit:
                # Truncate last chunk to fit
                remaining = context_limit - total_chars
                if remaining > 100:  # only add if meaningful
                    chunk_text = chunk_text[:remaining] + "..."
                else:
                    break

            citation_num = i + 1
            source_label = self._get_source_label(chunk)

            context_parts.append(
                f"[{citation_num}] {source_label}\n{chunk_text}"
            )

            citations.append({
                "citation_number": citation_num,
                "contract_id": chunk.contract_id,
                "clause_type": chunk.clause_type,
                "page": chunk.page,
                "rrf_score": chunk.rrf_score,
                "source": chunk.source,
                "text_preview": chunk_text[:100],
            })

            total_chars += len(chunk_text)

        context_text = "\n\n---\n\n".join(context_parts)

        logger.info(
            "context_retrieved",
            query=query[:50],
            chunks=len(chunks),
            context_chars=total_chars,
            plan=plan,
        )

        return RetrievedContext(
            chunks=chunks,
            context_text=context_text,
            citations=citations,
            query=query,
        )

    def _get_source_label(self, chunk: HybridSearchResult) -> str:
        """Human-readable source label for citation."""
        parts = []
        if chunk.clause_type:
            parts.append(chunk.clause_type.replace("_", " ").title())
        if chunk.page:
            parts.append(f"Page {chunk.page}")
        parts.append(f"[{chunk.source}]")
        return " | ".join(parts)


# Singleton
_retriever: RAGRetriever | None = None


def get_retriever() -> RAGRetriever:
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever
