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
    "free":         4000,   # was 2K
    "starter":      8000,   # was 4K
    "professional": 20000,  # was 8K — full tables need more context
    "enterprise":   40000,  # was 16K
}

# Top-K results per plan
TOP_K_LIMITS = {
    "free":         4,    # was 2
    "starter":      8,    # was 4
    "professional": 15,   # was 6 — tables/schedules need more chunks
    "enterprise":   25,   # was 10
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
        raw_query: str | None = None,
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

        # Multi-query hybrid search — decomposes broad queries
        chunks = await self._multi_query_search(
            query=query,
            org_id=org_id,
            db=db,
            contract_id=contract_id,
            top_k=top_k,
            clause_type=clause_type,
            raw_query=raw_query,
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


    async def _decompose_query(self, query: str) -> list[str]:
        """
        Decompose a broad query into focused sub-queries.
        Uses a fast LLM call to split multi-topic questions.
        Only decomposes if query is broad (>1 topic).
        """
        # Simple heuristic: skip decomposition for short/focused queries
        broad_signals = [
            " and ", " & ", "key risks", "summary", "overview",
            "all ", "main ", "important ", "critical ",
            "payment", "obligations", "dues",
        ]
        is_broad = len(query.split()) > 8 or any(s in query.lower() for s in broad_signals)
        if not is_broad:
            return [query]

        try:
            from app.infrastructure.llm.router import get_llm_router
            router = get_llm_router()
            prompt = (
                "Decompose this contract question into 3-5 focused sub-queries "
                "that each target a specific topic. Return ONLY a JSON array of strings. "
                "No explanation.\n\n"
                f"Question: {query}\n\n"
                "Example output: [\"liability cap and limitations\", \"payment terms and due dates\", \"termination rights\"]"
            )
            from app.infrastructure.llm.base import LLMMessage, AgentRole
            result = await router.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                role=AgentRole.EXTRACTOR,
            )
            import json
            text = result.content.strip()
            # Clean markdown fences if present
            text = text.replace("```json", "").replace("```", "").strip()
            sub_queries = json.loads(text)
            if isinstance(sub_queries, list) and len(sub_queries) >= 2:
                logger.info("query_decomposed", original=query[:50], sub_queries=len(sub_queries))
                return sub_queries[:5]
        except Exception as e:
            logger.warning("query_decomposition_failed", error=str(e)[:100])

        return [query]

    async def _multi_query_search(
        self,
        query: str,
        org_id: UUID,
        db: AsyncSession,
        contract_id: UUID | None,
        top_k: int,
        clause_type: str | None,
        raw_query: str | None,
    ) -> list[HybridSearchResult]:
        """
        Run multiple focused searches and merge results.
        Deduplicates by chunk text, keeps highest score.
        """
        sub_queries = await self._decompose_query(query)

        if len(sub_queries) <= 1:
            return await self.hybrid_engine.search(
                query=query, org_id=org_id, db=db,
                contract_id=contract_id, top_k=top_k,
                clause_type=clause_type, raw_query=raw_query,
            )

        # Run all sub-queries
        all_chunks: list[HybridSearchResult] = []
        seen_texts: set[str] = set()

        for sq in sub_queries:
            chunks = await self.hybrid_engine.search(
                query=sq, org_id=org_id, db=db,
                contract_id=contract_id, top_k=top_k,
                clause_type=clause_type, raw_query=raw_query,
            )
            for chunk in chunks:
                # Deduplicate by text preview (first 200 chars)
                key = chunk.text[:200]
                if key not in seen_texts:
                    seen_texts.add(key)
                    all_chunks.append(chunk)

        # Sort by RRF score descending, take top results
        all_chunks.sort(key=lambda c: c.rrf_score, reverse=True)
        result = all_chunks[:top_k + 5]  # slightly more for broad queries

        logger.info("multi_query_results",
                     sub_queries=len(sub_queries),
                     total_chunks=len(all_chunks),
                     deduped=len(result))
        return result

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
