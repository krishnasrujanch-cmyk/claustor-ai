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
    "free":         4,
    "starter":      8,
    "professional": 12,
    "enterprise":   15,  # rerank picks best 15 from 30 retrieved
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

        # Broad queries: load ALL chunks for the contract, then rerank
        # Focused queries: search-based retrieval, then rerank
        ]

        if contract_id:
            chunks = await self._retrieve_all_chunks(db, contract_id)
            if chunks:
                chunks = await self._rerank(query, chunks, top_n=min(len(chunks), 20))
                logger.info("broad_full_retrieval",
                             query=query[:50], total_chunks=len(chunks))
        else:
            chunks = await self.hybrid_engine.search(
                query=query, org_id=org_id, db=db,
                contract_id=contract_id, top_k=top_k,
                clause_type=clause_type, raw_query=raw_query,
            )
            if chunks:
                chunks = await self._rerank(
                    query, chunks, top_n=min(len(chunks), top_k + 5))

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


    async def _retrieve_all_chunks(self, db, contract_id) -> list:
        """
        Load ALL chunks for a specific contract from the database.
        Used for broad analytical queries where the entire contract
        is the analysis scope — no search filtering.
        """
        try:
            from sqlalchemy import text as sa_text
            r = await db.execute(sa_text(
                "SELECT text, chunk_type "
                "FROM contract_chunks "
                "WHERE contract_id = :cid "
                "AND chunk_type != 'signature' "
                "AND is_parent = false "
                "ORDER BY chunk_index"
            ), {"cid": str(contract_id)})
            rows = r.fetchall()
            if not rows:
                return []
            chunks = []
            for row in rows:
                if not row[0] or len(row[0].strip()) < 50:
                    continue
                chunks.append(HybridSearchResult(
                    text=row[0],
                    contract_id=str(contract_id),
                    clause_type=row[1] or "",
                    page=None,
                    rrf_score=1.0,
                    source="db_full",
                    keyword_score=0.0,
                    semantic_score=0.0,
                ))
            logger.info("all_chunks_loaded",
                         contract_id=str(contract_id),
                         count=len(chunks))
            return chunks
        except Exception as e:
            logger.warning("all_chunks_load_failed", error=str(e)[:100])
            return []

    async def _rerank(self, query: str, chunks: list, top_n: int = 12) -> list:
        """
        Rerank retrieved chunks using Cohere rerank API.
        Takes query + chunks, returns chunks reordered by relevance.
        Generic — works for any query type, any contract.
        """
        if not chunks or len(chunks) <= top_n:
            return chunks

        try:
            import httpx
            from app.core.config import settings

            docs = [c.text[:2000] for c in chunks]  # Cohere rerank max ~4K per doc

            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    "https://api.cohere.com/v2/rerank",
                    headers={
                        "Authorization": f"Bearer {settings.COHERE_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "rerank-multilingual-v3.0",
                        "query": query,
                        "documents": docs,
                        "top_n": top_n,
                    },
                )
                r.raise_for_status()

            results = r.json().get("results", [])
            reranked = []
            for result in results:
                idx = result["index"]
                chunk = chunks[idx]
                chunk.rrf_score = result["relevance_score"]  # override with rerank score
                reranked.append(chunk)

            logger.info("rerank_complete",
                        input=len(chunks), output=len(reranked),
                        top_score=round(reranked[0].rrf_score, 4) if reranked else 0)
            return reranked

        except Exception as e:
            logger.warning("rerank_failed", error=str(e)[:100])
            return chunks[:top_n]  # fallback: just truncate

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
