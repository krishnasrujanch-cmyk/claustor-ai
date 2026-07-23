"""
Claustor AI — Hybrid Search
Combines Pinecone semantic search + PostgreSQL full-text search.
Uses Reciprocal Rank Fusion (RRF) to merge results.
"""

import asyncio
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.vector_store.pinecone_store import get_vector_store

logger = structlog.get_logger(__name__)

RRF_K = 60
SEMANTIC_WEIGHT = 0.6
KEYWORD_WEIGHT  = 0.7


class HybridSearchResult:
    def __init__(self, text, contract_id, chunk_index, clause_type,
                 page, semantic_score=0.0, keyword_score=0.0,
                 rrf_score=0.0, source="hybrid"):
        self.text = text
        self.contract_id = contract_id
        self.chunk_index = chunk_index
        self.clause_type = clause_type
        self.page = page
        self.semantic_score = semantic_score
        self.keyword_score = keyword_score
        self.rrf_score = rrf_score
        self.source = source

    def to_dict(self):
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

    def __init__(self):
        self.vector_store = get_vector_store()

    async def search(
        self,
        query: str,
        org_id: UUID,
        db: AsyncSession,
        contract_id: UUID | None = None,
        top_k: int = 6,
        semantic_top_k: int = 15,
        keyword_top_k: int = 15,
        clause_type: str | None = None,
    ) -> list[HybridSearchResult]:

        # Run both searches in parallel
        semantic_task = asyncio.create_task(
            self._semantic_search(query, org_id, contract_id, semantic_top_k, clause_type)
        )
        keyword_task = asyncio.create_task(
            self._keyword_search(query, org_id, db, contract_id, keyword_top_k, clause_type)
        )

        semantic_results, keyword_results = await asyncio.gather(
            semantic_task, keyword_task, return_exceptions=True
        )

        if isinstance(semantic_results, Exception):
            logger.warning("semantic_search_failed", error=str(semantic_results))
            semantic_results = []
        if isinstance(keyword_results, Exception):
            logger.warning("keyword_search_failed", error=str(keyword_results))
            keyword_results = []

        logger.info(
            "hybrid_search_raw",
            semantic_hits=len(semantic_results),
            keyword_hits=len(keyword_results),
        )

        fused = self._rrf(semantic_results, keyword_results, top_k)
        return fused

    async def _semantic_search(self, query, org_id, contract_id, top_k, clause_type):
        return await self.vector_store.search(
            org_id=org_id,
            query=query,
            top_k=top_k,
            contract_id=contract_id,
            clause_type=clause_type,
        )

    async def _keyword_search(
        self,
        query: str,
        org_id: UUID,
        db: AsyncSession,
        contract_id: UUID | None,
        top_k: int,
        clause_type: str | None,
    ) -> list[dict]:

        try:
            # Build WHERE conditions
            conditions = ["c.org_id::text = :org_id"]
            params = {
                "org_id": str(org_id),
                "query": query,
            }

            if contract_id:
                conditions.append("c.contract_id::text = :contract_id")
                params["contract_id"] = str(contract_id)

            if clause_type:
                conditions.append("c.clause_type = :clause_type")
                params["clause_type"] = clause_type

            where = " AND ".join(conditions)

            sql = text(f"""
                SELECT
                    c.id::text          AS id,
                    c.contract_id::text AS contract_id,
                    c.raw_text          AS text,
                    c.clause_type,
                    0                   AS page,
                    ts_rank(
                        to_tsvector('english',
                            COALESCE(c.raw_text, '') || ' ' ||
                            COALESCE(c.summary,  '') || ' ' ||
                            COALESCE(c.title,    '')
                        ),
                        plainto_tsquery('english', :query)
                    ) AS keyword_score
                FROM clauses c
                WHERE
                    {where}
                    AND to_tsvector('english',
                        COALESCE(c.raw_text, '') || ' ' ||
                        COALESCE(c.summary,  '') || ' ' ||
                        COALESCE(c.title,    '')
                    ) @@ plainto_tsquery('english', :query)
                ORDER BY keyword_score DESC
                LIMIT 15
            """)

            result = await db.execute(sql, params)
            rows = result.fetchall()

            logger.info("keyword_search_results", count=len(rows), query=query[:30])

            return [
                {
                    "text": row.text or "",
                    "contract_id": row.contract_id,
                    "chunk_index": 0,
                    "clause_type": row.clause_type or "",
                    "page": 0,
                    "score": float(row.keyword_score),
                    "source": "keyword",
                }
                for row in rows
            ]

        except Exception as e:
            logger.warning("keyword_search_error", error=str(e))
            try:
                await db.rollback()
            except Exception:
                pass
            return []

    def _rrf(self, semantic_results, keyword_results, top_k):
        scores: dict[str, dict] = {}

        for rank, r in enumerate(semantic_results):
            key = f"{r.get('contract_id','')}__{r.get('text','')[:40]}"
            if key not in scores:
                scores[key] = {"result": r, "sem_rrf": 0.0, "kw_rrf": 0.0, "sem_rank": None, "kw_rank": None}
            scores[key]["sem_rrf"] = SEMANTIC_WEIGHT / (RRF_K + rank)
            scores[key]["sem_rank"] = rank

        for rank, r in enumerate(keyword_results):
            key = f"{r.get('contract_id','')}__{r.get('text','')[:40]}"
            if key not in scores:
                scores[key] = {"result": r, "sem_rrf": 0.0, "kw_rrf": 0.0, "sem_rank": None, "kw_rank": None}
            scores[key]["kw_rrf"] = KEYWORD_WEIGHT / (RRF_K + rank)
            scores[key]["kw_rank"] = rank

        fused = []
        for key, data in scores.items():
            rrf = data["sem_rrf"] + data["kw_rrf"]
            r = data["result"]

            if data["sem_rank"] is not None and data["kw_rank"] is not None:
                source = "hybrid"
            elif data["sem_rank"] is not None:
                source = "semantic"
            else:
                source = "keyword"

            fused.append(HybridSearchResult(
                text=r.get("text", ""),
                contract_id=r.get("contract_id", ""),
                chunk_index=r.get("chunk_index", 0),
                clause_type=r.get("clause_type", ""),
                page=r.get("page", 0),
                semantic_score=r.get("score", 0.0) if source != "keyword" else 0.0,
                keyword_score=r.get("score", 0.0) if source == "keyword" else 0.0,
                rrf_score=rrf,
                source=source,
            ))

        fused.sort(key=lambda x: x.rrf_score, reverse=True)

        # Guarantee at least 1 keyword/hybrid result in final set
        # This is correct — keyword finds exact matches semantic misses
        top = fused[:top_k]
        has_kw = any(r.source in ("keyword", "hybrid") for r in top)
        if not has_kw:
            kw_results = [r for r in fused[top_k:] if r.source == "keyword"]
            if kw_results:
                top = top[:-1] + [kw_results[0]]
        return top


_hybrid_engine: HybridSearchEngine | None = None


def get_hybrid_search() -> HybridSearchEngine:
    global _hybrid_engine
    if _hybrid_engine is None:
        _hybrid_engine = HybridSearchEngine()
    return _hybrid_engine
