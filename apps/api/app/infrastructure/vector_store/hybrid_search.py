"""
Claustor AI — Hybrid Search
Combines Pinecone semantic search + PostgreSQL full-text search.
Uses Reciprocal Rank Fusion (RRF) to merge and re-rank results.

Why hybrid:
  Semantic: finds "damages" when query says "liability" (meaning)
  Keyword:  finds "Section 8.1", "USD 1,000,000" (exact match)
  RRF:      combines both, best of both worlds
"""

import math
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.vector_store.pinecone_store import get_vector_store

logger = structlog.get_logger(__name__)

# RRF constant — higher = smoother ranking, 60 is standard
RRF_K = 60

# Weight balance between semantic and keyword
SEMANTIC_WEIGHT = 0.7   # semantic wins for concepts
KEYWORD_WEIGHT  = 0.3   # keyword wins for exact terms


class HybridSearchResult:
    """Single search result with combined score."""

    def __init__(
        self,
        text: str,
        contract_id: str,
        chunk_index: int,
        clause_type: str,
        page: int,
        semantic_score: float = 0.0,
        keyword_score: float = 0.0,
        rrf_score: float = 0.0,
        source: str = "hybrid",
    ):
        self.text = text
        self.contract_id = contract_id
        self.chunk_index = chunk_index
        self.clause_type = clause_type
        self.page = page
        self.semantic_score = semantic_score
        self.keyword_score = keyword_score
        self.rrf_score = rrf_score
        self.source = source

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "contract_id": self.contract_id,
            "chunk_index": self.chunk_index,
            "clause_type": self.clause_type,
            "page": self.page,
            "semantic_score": round(self.semantic_score, 4),
            "keyword_score": round(self.keyword_score, 4),
            "rrf_score": round(self.rrf_score, 4),
            "source": self.source,
        }


class HybridSearchEngine:
    """
    Production hybrid search engine.

    Semantic search:  Pinecone (vector similarity)
    Keyword search:   PostgreSQL full-text search (tsvector/tsquery)
    Fusion:           Reciprocal Rank Fusion (RRF)
    """

    def __init__(self):
        self.vector_store = get_vector_store()

    async def search(
        self,
        query: str,
        org_id: UUID,
        db: AsyncSession,
        contract_id: UUID | None = None,
        top_k: int = 6,
        semantic_top_k: int = 15,  # fetch more, re-rank to top_k
        keyword_top_k: int = 15,
        clause_type: str | None = None,
    ) -> list[HybridSearchResult]:
        """
        Hybrid search combining semantic + keyword retrieval.

        Args:
            query:          Natural language query
            org_id:         Organisation (namespace isolation)
            db:             DB session for PostgreSQL FTS
            contract_id:    Optional — search within specific contract
            top_k:          Final results to return after re-ranking
            semantic_top_k: Semantic candidates before fusion
            keyword_top_k:  Keyword candidates before fusion
            clause_type:    Optional filter by clause type

        Returns:
            Re-ranked list of HybridSearchResult
        """

        # Run both searches in parallel
        import asyncio
        semantic_task = asyncio.create_task(
            self._semantic_search(
                query=query,
                org_id=org_id,
                contract_id=contract_id,
                top_k=semantic_top_k,
                clause_type=clause_type,
            )
        )
        keyword_task = asyncio.create_task(
            self._keyword_search(
                query=query,
                org_id=org_id,
                db=db,
                contract_id=contract_id,
                top_k=keyword_top_k,
                clause_type=clause_type,
            )
        )

        semantic_results, keyword_results = await asyncio.gather(
            semantic_task, keyword_task, return_exceptions=True
        )

        # Handle errors gracefully — degrade to available source
        if isinstance(semantic_results, Exception):
            logger.warning("semantic_search_failed", error=str(semantic_results))
            semantic_results = []
        if isinstance(keyword_results, Exception):
            logger.warning("keyword_search_failed", error=str(keyword_results))
            keyword_results = []

        # Fuse results using RRF
        fused = self._reciprocal_rank_fusion(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            top_k=top_k,
        )

        logger.info(
            "hybrid_search_complete",
            query=query[:50],
            semantic_hits=len(semantic_results),
            keyword_hits=len(keyword_results),
            fused_results=len(fused),
            top_score=fused[0].rrf_score if fused else 0,
        )

        return fused

    async def _semantic_search(
        self,
        query: str,
        org_id: UUID,
        contract_id: UUID | None,
        top_k: int,
        clause_type: str | None,
    ) -> list[dict]:
        """Pinecone semantic search."""
        results = await self.vector_store.search(
            org_id=org_id,
            query=query,
            top_k=top_k,
            contract_id=contract_id,
            clause_type=clause_type,
        )
        return results

    async def _keyword_search(
        self,
        query: str,
        org_id: UUID,
        db: AsyncSession,
        contract_id: UUID | None,
        top_k: int,
        clause_type: str | None,
    ) -> list[dict]:
        """
        PostgreSQL full-text search on clauses table.
        Uses tsvector for efficient indexing.
        Handles: exact terms, numbers, section references.
        """

        # Build plainto_tsquery — safe, handles any input
        # plainto_tsquery('liability cap section 8') →
        #   'liabil' & 'cap' & 'section' & '8'
        filters = ["c.org_id = :org_id"]
        params: dict = {"org_id": org_id, "query": query, "limit": top_k}

        if contract_id:
            filters.append("c.contract_id = :contract_id")
            params["contract_id"] = contract_id

        if clause_type:
            filters.append("c.clause_type = :clause_type")
            params["clause_type"] = clause_type

        where_clause = " AND ".join(filters)

        sql = text(f"""
            SELECT
                c.id::text         AS id,
                c.contract_id::text AS contract_id,
                c.raw_text         AS text,
                c.clause_type,
                0                  AS page,
                ts_rank(
                    to_tsvector('english', COALESCE(c.raw_text, '') || ' ' || COALESCE(c.summary, '') || ' ' || COALESCE(c.title, '')),
                    plainto_tsquery('english', :query)
                ) AS keyword_score
            FROM clauses c
            WHERE
                {where_clause}
                AND to_tsvector('english',
                    COALESCE(c.raw_text, '') || ' ' ||
                    COALESCE(c.summary, '') || ' ' ||
                    COALESCE(c.title, '')
                ) @@ plainto_tsquery('english', :query)
            ORDER BY keyword_score DESC
            LIMIT :limit
        """)

        result = await db.execute(sql, params)
        rows = result.fetchall()

        return [
            {
                "text": row.text or "",
                "contract_id": row.contract_id,
                "chunk_index": 0,
                "clause_type": row.clause_type or "",
                "page": row.page or 0,
                "score": float(row.keyword_score),
                "source": "keyword",
            }
            for row in rows
        ]

    def _reciprocal_rank_fusion(
        self,
        semantic_results: list[dict],
        keyword_results: list[dict],
        top_k: int,
    ) -> list[HybridSearchResult]:
        """
        Reciprocal Rank Fusion (RRF) algorithm.

        RRF score = Σ weight / (k + rank)

        For each unique chunk:
          semantic_score = SEMANTIC_WEIGHT / (RRF_K + semantic_rank)
          keyword_score  = KEYWORD_WEIGHT  / (RRF_K + keyword_rank)
          rrf_score      = semantic_score + keyword_score

        Higher RRF score = more relevant result.
        """

        # Build score map keyed by (contract_id, chunk_index or text hash)
        scores: dict[str, dict] = {}

        # Score semantic results
        for rank, result in enumerate(semantic_results):
            key = self._result_key(result)
            if key not in scores:
                scores[key] = {
                    "result": result,
                    "semantic_rank": None,
                    "keyword_rank": None,
                    "semantic_rrf": 0.0,
                    "keyword_rrf": 0.0,
                }
            scores[key]["semantic_rank"] = rank
            scores[key]["semantic_rrf"] = SEMANTIC_WEIGHT / (RRF_K + rank)

        # Score keyword results
        for rank, result in enumerate(keyword_results):
            key = self._result_key(result)
            if key not in scores:
                scores[key] = {
                    "result": result,
                    "semantic_rank": None,
                    "keyword_rank": None,
                    "semantic_rrf": 0.0,
                    "keyword_rrf": 0.0,
                }
            scores[key]["keyword_rank"] = rank
            scores[key]["keyword_rrf"] = KEYWORD_WEIGHT / (RRF_K + rank)

        # Calculate final RRF score
        fused = []
        for key, data in scores.items():
            rrf_score = data["semantic_rrf"] + data["keyword_rrf"]
            result = data["result"]

            # Determine source
            if data["semantic_rank"] is not None and data["keyword_rank"] is not None:
                source = "hybrid"
            elif data["semantic_rank"] is not None:
                source = "semantic"
            else:
                source = "keyword"

            fused.append(HybridSearchResult(
                text=result.get("text", ""),
                contract_id=result.get("contract_id", ""),
                chunk_index=result.get("chunk_index", 0),
                clause_type=result.get("clause_type", ""),
                page=result.get("page", 0),
                semantic_score=result.get("score", 0.0) if source != "keyword" else 0.0,
                keyword_score=result.get("score", 0.0) if source == "keyword" else 0.0,
                rrf_score=rrf_score,
                source=source,
            ))

        # Sort by RRF score descending, return top_k
        fused.sort(key=lambda x: x.rrf_score, reverse=True)
        return fused[:top_k]

    def _result_key(self, result: dict) -> str:
        """
        Unique key for deduplication across semantic + keyword results.
        Uses contract_id + first 50 chars of text as fingerprint.
        """
        contract_id = result.get("contract_id", "")
        text_fp = result.get("text", "")[:50]
        return f"{contract_id}::{text_fp}"


# Singleton
_hybrid_engine: HybridSearchEngine | None = None


def get_hybrid_search() -> HybridSearchEngine:
    """Get or create singleton hybrid search engine."""
    global _hybrid_engine
    if _hybrid_engine is None:
        _hybrid_engine = HybridSearchEngine()
    return _hybrid_engine
