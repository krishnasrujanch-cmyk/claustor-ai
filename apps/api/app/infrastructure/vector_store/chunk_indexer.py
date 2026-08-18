"""
Claustor AI — Chunk Indexer
Saves ContractChunkData to PostgreSQL (BM25) + Pinecone (vectors).
"""

from __future__ import annotations
import asyncio
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings, delete

logger = logging.getLogger(__name__)

PINECONE_BATCH_SIZE = 100
EMBED_BATCH_SIZE = 32


async def index_chunks(
    chunks: list,
    contract_id: UUID,
    org_id: UUID,
    db: AsyncSession,
    vector_store,
) -> None:
    """
    Save chunks to PostgreSQL (BM25) and Pinecone (vectors).
    Deletes old chunks first for clean reindex.
    """
    # ── Step 1: Delete old chunks ──
    await db.execute(
        text("DELETE FROM contract_chunks WHERE contract_id = :cid"),
        {"cid": str(contract_id)}
    )
    logger.info(f"old_chunks_deleted: contract_id={contract_id}")

    # ── Step 2: Delete old Pinecone vectors ──
    try:
        await vector_store.delete_contract(org_id, contract_id)
    except Exception as e:
        logger.warning(f"pinecone_delete_failed: {e}")

    # ── Step 3: Save to PostgreSQL ──
    from app.domain.models import ContractChunk

    db_chunks = []
    for chunk in chunks:
        db_chunk = ContractChunk(
            id          = chunk.chunk_id,
            contract_id = chunk.contract_id,
            org_id      = chunk.org_id,
            parent_id   = chunk.parent_id,
            is_parent   = chunk.is_parent,
            chunk_type  = chunk.chunk_type,
            chunk_index = chunk.chunk_index,
            text        = chunk.text,
            heading     = chunk.heading,
            section_ref = chunk.section_ref,
            page_number = chunk.page_number,
            risk_score  = chunk.risk_score,
            importance  = chunk.importance,
            cross_refs  = chunk.cross_refs or [],
            table_json  = chunk.table_json,
        )
        db_chunks.append(db_chunk)

    db.add_all(db_chunks)
    await db.flush()  # flush but don't commit — pipeline handles the transaction
    logger.info(f"chunks_saved_postgres: count={len(db_chunks)} contract_id={contract_id}")

    # ── Step 4: Embed + Upsert to Pinecone ──
    # Only embed non-signature chunks
    embeddable = [c for c in chunks if c.chunk_type != "signature"]

    # Embed in batches
    embedder = await vector_store.get_embedder()
    loop = asyncio.get_event_loop()

    pinecone_vectors = []
    for i in range(0, len(embeddable), EMBED_BATCH_SIZE):
        batch = embeddable[i:i+EMBED_BATCH_SIZE]
        texts = [c.text for c in batch]

        embeddings = await loop.run_in_executor(
            None,
            lambda t=texts: embedder.encode(t, normalize_embeddings=True).tolist()
        )

        for chunk, embedding in zip(batch, embeddings):
            pinecone_id = f"chunk_{chunk.chunk_id}"
            metadata = {
                "chunk_id":      str(chunk.chunk_id),
                "contract_id":   str(chunk.contract_id),
                "org_id":        str(chunk.org_id),
                "parent_id":     str(chunk.parent_id) if chunk.parent_id else "",
                "is_parent":     chunk.is_parent,
                "chunk_type":    chunk.chunk_type,
                "section_ref":   chunk.section_ref or "",
                "heading":       (chunk.heading or "")[:500],
                "importance":    chunk.importance or "low",
                "risk_level":    chunk.risk_level or "",
                "risk_score":    chunk.risk_score or 0.0,
                "contract_type": chunk.contract_type or "",
                "counterparty":  (chunk.counterparty or "")[:200],
                "expiry_date":   chunk.expiry_date or "",
                "effective_date":chunk.effective_date or "",
                # Store short text preview for context (not full text)
                "text_preview":  chunk.text[:200],
            }
            pinecone_vectors.append((pinecone_id, embedding, metadata))


    # Upsert to Pinecone in batches
    if pinecone_vectors:
        namespace = f"org_{str(org_id).replace('-','')[:8]}"
        idx = vector_store.index
        for i in range(0, len(pinecone_vectors), PINECONE_BATCH_SIZE):
            batch = pinecone_vectors[i:i+PINECONE_BATCH_SIZE]
            vectors = [{"id": v[0], "values": v[1], "metadata": v[2]} for v in batch]
            await loop.run_in_executor(
                None,
                lambda v=vectors: idx.upsert(vectors=v, namespace=namespace)
            )
    # Batch update pinecone_ids in DB after ALL Pinecone upserts complete
    # Use fresh connection to avoid "connection closed" error
    if pinecone_vectors:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        import ssl as _ssl
        _ssl_ctx = _ssl.create_default_context()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            connect_args={"ssl": _ssl_ctx},
            pool_pre_ping=True,
        )
        try:
            _factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
            async with _factory() as _fresh_db:
                for _pid, _, _ in pinecone_vectors:
                    _cid = _pid.replace("chunk_", "")
                    try:
                        await _fresh_db.execute(
                            text("UPDATE contract_chunks SET pinecone_id = :pid WHERE id = :cid"),
                            {"pid": _pid, "cid": _cid}
                        )
                    except Exception as _ue:
                        logger.warning("chunk_id_update_failed", chunk_id=_cid, error=str(_ue))
                await _fresh_db.commit()
        finally:
            await _engine.dispose()
        logger.info(f"chunks_indexed_pinecone: count={len(pinecone_vectors)} contract_id={contract_id}")

    logger.info(f"chunk_indexing_complete: total={len(chunks)} embedded={len(embeddable)} contract_id={contract_id}")


async def fetch_chunk_texts(
    chunk_ids: list[str],
    db: AsyncSession,
) -> dict[str, str]:
    """Fetch full text for chunk IDs from PostgreSQL."""
    if not chunk_ids:
        return {}
    # Strip "chunk_" prefix if present (Pinecone IDs use this prefix)
    clean_ids = [cid.replace("chunk_", "") if cid.startswith("chunk_") else cid
                 for cid in chunk_ids]
    placeholders = ",".join(f"'{cid}'" for cid in clean_ids)
    r = await db.execute(text(f"""
        SELECT id::text, text, parent_id::text, heading, section_ref
        FROM contract_chunks
        WHERE id::text IN ({placeholders})
    """))
    return {
        str(row[0]): {
            "text": row[1],
            "parent_id": str(row[2]) if row[2] else None,
            "heading": row[3],
            "section_ref": row[4],
        }
        for row in r.fetchall()
    }


async def fetch_parent_texts(
    parent_ids: list[str],
    db: AsyncSession,
) -> dict[str, str]:
    """Fetch parent chunk texts for multi-level retrieval."""
    if not parent_ids:
        return {}
    clean_ids = [pid.replace("chunk_", "") if pid and pid.startswith("chunk_") else pid
                  for pid in parent_ids if pid]
    if not clean_ids:
        return {}
    placeholders = ",".join(f"'{pid}'" for pid in clean_ids)
    r = await db.execute(text(f"""
        SELECT id::text, text, heading, section_ref
        FROM contract_chunks
        WHERE id::text IN ({placeholders}) AND is_parent = TRUE
    """))
    return {
        str(row[0]): {
            "text": row[1],
            "heading": row[2],
            "section_ref": row[3],
        }
        for row in r.fetchall()
    }


async def bm25_search(  # DEBUG VERSION

    query: str,
    org_id: UUID,
    db: AsyncSession,
    contract_id: Optional[UUID] = None,
    top_k: int = 10,
    exclude_types: list[str] = None,
) -> list[dict]:
    """
    BM25 full-text search on contract_chunks table.
    Returns chunk dicts with text and metadata.
    """
    exclude_types = exclude_types or ["signature"]
    # Build exclude clause — use NOT IN with literals to avoid array param issues
    exclude_list = ",".join(f"'{t}'" for t in (exclude_types or ["signature"]))
    conditions = [
        "org_id = :org_id",
        f"chunk_type NOT IN ({exclude_list})",
        "to_tsvector('simple', text) @@ plainto_tsquery('simple', :query)",
    ]
    params = {
        "org_id": str(org_id),
        "query": query,
    }
    if contract_id:
        conditions.append("contract_id = :contract_id")
        params["contract_id"] = str(contract_id)

    where = " AND ".join(conditions)
    try:
        r = await db.execute(text(f"""
            SELECT
                id::text, text, heading, section_ref, chunk_type,
                parent_id::text, importance, risk_score,
                ts_rank(to_tsvector('simple', text),
                        plainto_tsquery('simple', :query)) AS score
            FROM contract_chunks
            WHERE {where}
            ORDER BY score DESC
            LIMIT {top_k}
        """), params)
        rows = r.fetchall()
        return [
            {
                "id":          row[0],
                "text":        row[1],
                "heading":     row[2],
                "section_ref": row[3],
                "chunk_type":  row[4],
                "parent_id":   row[5],
                "importance":  row[6],
                "risk_score":  row[7],
                "bm25_score":  float(row[8]),
            }
            for row in rows
        ]
    except Exception as e:
        logger.warning(f"bm25_search_error: {e}")
        return []

async def fetch_cross_ref_chunks(
    chunk_ids: list[str],
    db: AsyncSession,
) -> list[dict]:
    """
    Fetch chunks referenced by cross_refs of given chunks.
    Returns additional context chunks from cross-referenced sections.
    """
    if not chunk_ids:
        return []
    clean_ids = [cid.replace("chunk_","") if cid.startswith("chunk_") else cid
                 for cid in chunk_ids]
    placeholders = ",".join(f"\'{cid}\'" for cid in clean_ids)
    try:
        # Get cross_refs from retrieved chunks
        r = await db.execute(text(f"""
            SELECT cross_refs, contract_id::text, org_id::text
            FROM contract_chunks
            WHERE id::text IN ({placeholders})
              AND cross_refs != '[]'
              AND cross_refs IS NOT NULL
        """))
        rows = r.fetchall()
        if not rows:
            return []

        # Extract section references and find matching chunks
        all_refs = []
        contract_id = rows[0][1]
        org_id = rows[0][2]
        for row in rows:
            refs = row[0] or []
            all_refs.extend(refs)

        if not all_refs:
            return []

        # Search for chunks matching cross-references by heading/section_ref
        ref_conditions = " OR ".join([
            f"heading ILIKE '%{ref.split()[-1][:20]}%' OR section_ref ILIKE '%{ref.split()[-1][:20]}%'"
            for ref in all_refs[:5]  # limit to 5 refs
        ])

        r2 = await db.execute(text(f"""
            SELECT id::text, text, heading, section_ref, chunk_type
            FROM contract_chunks
            WHERE contract_id = '{contract_id}'
              AND is_parent = TRUE
              AND ({ref_conditions})
            LIMIT 3
        """))
        return [
            {
                "id": row[0], "text": row[1],
                "heading": row[2], "section_ref": row[3],
                "chunk_type": row[4], "source": "cross_ref",
            }
            for row in r2.fetchall()
        ]
    except Exception as e:
        logger.warning(f"cross_ref_fetch_error: {e}")
        return []

