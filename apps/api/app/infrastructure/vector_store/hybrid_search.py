"""
Claustor AI — Hybrid Search Engine
Combines Pinecone semantic search + PostgreSQL BM25 full-text search.
"""

import asyncio
from uuid import UUID
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

RRF_K = 60
SEMANTIC_WEIGHT = 0.6
KEYWORD_WEIGHT  = 0.7


class HybridSearchResult:
    def __init__(self, text="", contract_id="", chunk_index=0, clause_type="",
                 page=0, semantic_score=0.0, keyword_score=0.0,
                 rrf_score=0.0, source="hybrid", chunk_id="", id="",
                 parent_id=None, heading=None, is_parent=False):
        self.text           = text
        self.contract_id    = contract_id
        self.chunk_index    = chunk_index
        self.clause_type    = clause_type
        self.page           = page
        self.semantic_score = semantic_score
        self.keyword_score  = keyword_score
        self.rrf_score      = rrf_score
        self.source         = source
        self.chunk_id       = chunk_id or id or ""
        self.id             = self.chunk_id
        self.parent_id      = parent_id
        self.heading        = heading
        self.is_parent      = is_parent

    def to_dict(self):
        return {
            "text": self.text, "contract_id": self.contract_id,
            "chunk_index": self.chunk_index, "clause_type": self.clause_type,
            "chunk_id": self.chunk_id, "heading": self.heading,
            "rrf_score": round(self.rrf_score, 4),
        }


class HybridSearchEngine:
    def __init__(self):
        pass

    async def search(
        self, query, org_id, db, contract_id=None,
        top_k=10, semantic_top_k=20, keyword_top_k=15, clause_type=None,
        raw_query=None,
    ):
        # Semantic uses rewritten query (richer), BM25 uses raw query (keywords)
        bm25_query = raw_query or query
        # BM25 first (fast <1s), then semantic (slow on cold start)
        try:
            kw = await self._keyword_search(bm25_query, org_id, db, contract_id, keyword_top_k, clause_type)
        except Exception as e:
            logger.warning(f"keyword_search_failed: {e}"); kw = []
        try:
            sem = await self._semantic_search(query, org_id, contract_id, semantic_top_k, clause_type)
        except Exception as e:
            logger.warning(f"semantic_search_failed: {e}"); sem = []
        logger.info("hybrid_search_raw", semantic_hits=len(sem), keyword_hits=len(kw))

        fused = self._rrf(sem, kw, top_k)

        def _get(r, k, d=""):
            return r.get(k, d) if isinstance(r, dict) else getattr(r, k, d) or d

        chunk_ids = list({_get(r,"chunk_id") or _get(r,"id") for r in fused
                          if _get(r,"chunk_id") or _get(r,"id")})

        if chunk_ids and db:
            try:
                from app.infrastructure.vector_store.chunk_indexer import (
                    fetch_chunk_texts, fetch_parent_texts)
                texts = await fetch_chunk_texts(chunk_ids, db)
                for r in fused:
                    cid = _get(r,"chunk_id") or _get(r,"id")
                    if cid and cid in texts:
                        if isinstance(r, HybridSearchResult):
                            r.text = texts[cid]["text"]
                            r.parent_id = texts[cid].get("parent_id")
                            r.heading = r.heading or texts[cid].get("heading","")
                        else:
                            r["text"] = texts[cid]["text"]

                pids = list({_get(r,"parent_id") for r in fused
                             if _get(r,"parent_id") and not _get(r,"is_parent")})
                if pids:
                    ptexts = await fetch_parent_texts(pids, db)
                    existing = {_get(r,"chunk_id") or _get(r,"id") for r in fused}
                    for pid, pd in ptexts.items():
                        if pid not in existing:
                            fused.append(HybridSearchResult(
                                chunk_id=pid, text=pd["text"],
                                heading=pd.get("heading",""),
                                is_parent=True, source="parent"))
                # Phase 3: Cross-reference retrieval
                try:
                    from app.infrastructure.vector_store.chunk_indexer import fetch_cross_ref_chunks
                    xref_chunks = await fetch_cross_ref_chunks(chunk_ids, db)
                    existing = {_get(r,"chunk_id") or _get(r,"id") for r in fused}
                    for xc in xref_chunks:
                        if xc["id"] not in existing:
                            fused.append(HybridSearchResult(
                                chunk_id=xc["id"],
                                text=xc["text"],
                                heading=xc.get("heading",""),
                                is_parent=True,
                                rrf_score=0.0,
                                source="cross_ref",
                            ))
                    if xref_chunks:
                        logger.info(f"cross_ref_chunks_added: {len(xref_chunks)}")
                except Exception as _xe:
                    logger.warning(f"cross_ref_error: {_xe}")

            except Exception as e:
                logger.warning(f"chunk_fetch_error: {e}")

        final = []
        for r in fused:
            if isinstance(r, HybridSearchResult) and r.text:
                final.append(r)
            elif isinstance(r, dict) and r.get("text"):
                final.append(HybridSearchResult(
                    chunk_id=r.get("chunk_id") or r.get("id",""),
                    text=r.get("text",""),
                    contract_id=r.get("contract_id",""),
                    chunk_index=r.get("chunk_index",0),
                    clause_type=r.get("chunk_type","") or r.get("clause_type",""),
                    page=r.get("page_number",0) or r.get("page",0),
                    semantic_score=r.get("vector_score",0.0),
                    keyword_score=r.get("bm25_score",0.0),
                    rrf_score=r.get("rrf_score",0.0),
                    source=r.get("source","hybrid"),
                    parent_id=r.get("parent_id"),
                    heading=r.get("heading"),
                ))
        return final[:top_k + 3]

    def _rrf(self, semantic, keyword, top_k):
        scores = {}
        all_results = {}
        def key_of(r, prefix, rank):
            k = r.get("chunk_id") or r.get("id","") if isinstance(r,dict)                 else getattr(r,"chunk_id","") or getattr(r,"id","")
            return k or f"{prefix}_{rank}"
        for rank, r in enumerate(semantic):
            k = key_of(r,"sem",rank)
            scores[k] = scores.get(k,0) + SEMANTIC_WEIGHT/(RRF_K+rank+1)
            all_results[k] = r
        for rank, r in enumerate(keyword):
            k = key_of(r,"kw",rank)
            scores[k] = scores.get(k,0) + KEYWORD_WEIGHT/(RRF_K+rank+1)
            if k not in all_results: all_results[k] = r
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        fused = []
        for k, rrf in ranked:
            r = all_results[k]
            if isinstance(r, HybridSearchResult):
                r.rrf_score = rrf; fused.append(r)
            elif isinstance(r, dict):
                fused.append(HybridSearchResult(
                    chunk_id=r.get("chunk_id") or r.get("id",""),
                    text=r.get("text",""), contract_id=r.get("contract_id",""),
                    chunk_index=r.get("chunk_index",0),
                    clause_type=r.get("clause_type","") or r.get("chunk_type",""),
                    page=r.get("page",0) or r.get("page_number",0),
                    semantic_score=r.get("vector_score",0.0),
                    keyword_score=r.get("bm25_score",0.0),
                    rrf_score=rrf, source="hybrid",
                    parent_id=r.get("parent_id"), heading=r.get("heading"),
                ))
        return fused

    async def _semantic_search(self, query, org_id, contract_id, top_k, clause_type):
        from app.infrastructure.vector_store.pinecone_store import get_vector_store
        vs = get_vector_store()
        namespace = f"org_{str(org_id).replace('-','')[:8]}"
        filt = {"org_id": str(org_id), "chunk_type": {"$nin": ["signature"]}}
        if contract_id: filt["contract_id"] = str(contract_id)
        if clause_type: filt["chunk_type"] = clause_type
        # HF Inference API — bge-m3 (0.38s vs 10s local, same model)
        from app.infrastructure.vector_store.pinecone_store import embed_query_cohere
        emb = await embed_query_cohere(query)
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(
                None, lambda: vs.index.query(
                    vector=emb, top_k=top_k, namespace=namespace,
                    filter=filt, include_metadata=True))
            matches = res.get("matches",[]) if isinstance(res,dict) else res.matches
        except Exception as e:
            logger.warning(f"pinecone_search_error: {e}"); return []
        results = []
        for m in matches:
            mid  = m["id"] if isinstance(m,dict) else m.id
            meta = m.get("metadata",{}) if isinstance(m,dict) else (m.metadata or {})
            score = m.get("score",0) if isinstance(m,dict) else m.score
            cid  = meta.get("chunk_id", mid.replace("chunk_",""))
            results.append({
                "chunk_id": cid, "id": cid,
                "text": meta.get("text_preview",""),
                "heading": meta.get("heading",""),
                "section_ref": meta.get("section_ref",""),
                "chunk_type": meta.get("chunk_type","clause"),
                "parent_id": meta.get("parent_id") or None,
                "vector_score": score,
                "contract_id": meta.get("contract_id",""),
            })
        logger.debug("vector_search", org_id=str(org_id), query=repr(query),
                     results=len(results),
                     top_score=max((r["vector_score"] for r in results), default=0))
        return results

    async def _keyword_search(self, query, org_id, db, contract_id, top_k, clause_type):
        from app.infrastructure.vector_store.chunk_indexer import bm25_search
        results = await bm25_search(
            query=query, org_id=org_id, db=db,
            contract_id=contract_id, top_k=top_k, exclude_types=["signature"])
        logger.info(f"bm25_search_results: count={len(results)} query={query[:30]!r}")
        return results


_engine = None
def get_hybrid_search():
    global _engine
    if _engine is None: _engine = HybridSearchEngine()
    return _engine
