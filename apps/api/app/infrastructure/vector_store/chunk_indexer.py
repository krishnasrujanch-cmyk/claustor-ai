"""
Claustor AI — Chunk Indexer
Saves ContractChunkData to PostgreSQL (BM25) + Pinecone (vectors).

Architecture: Two-phase design for long-running embedding operations.
  Phase A (fast <5s):  DELETE old + INSERT new chunks to PostgreSQL
  Phase B (slow 10min): bge-m3 embed + Pinecone upsert (NO DB held open)
"""

from __future__ import annotations
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

PINECONE_BATCH_SIZE = 100
EMBED_BATCH_SIZE = 32


async def index_chunks(
    chunks: list,
    contract_id: UUID,
    org_id: UUID,
    db: AsyncSession,
    vector_store,
    session_manager=None,
) -> None:
    """
    Two-phase indexing:
    Phase A: Save chunks to PostgreSQL (fast, commits immediately)
    Phase B: Embed + upsert to Pinecone (slow, no DB session held)
    """
    # ── Phase A: PostgreSQL save (fast, <5s) ──────────────────────────────────
    if session_manager:
        # Use fresh NullPool session — guaranteed alive
        async def _save_to_postgres(fresh_db: AsyncSession):
            await _phase_a_save(fresh_db, chunks, contract_id, org_id)
        await session_manager.execute(_save_to_postgres, operation_name="save_chunks_postgres")
    else:
        # Fallback: use passed db session
        await _phase_a_save(db, chunks, contract_id, org_id)

    # ── Phase B: Embed + Pinecone (slow, no DB) ───────────────────────────────
    await _phase_b_embed_and_index(chunks, contract_id, org_id, vector_store)


async def _phase_a_save(
    db: AsyncSession,
    chunks: list,
    contract_id: UUID,
    org_id: UUID,
) -> None:
    """Phase A: Delete old + save new chunks to PostgreSQL. Fast (<5s)."""
    from app.domain.models import ContractChunk

    # Delete old chunks
    await db.execute(
        text("DELETE FROM contract_chunks WHERE contract_id = :cid"),
        {"cid": str(contract_id)}
    )
    logger.info(f"old_chunks_deleted: contract_id={contract_id}")

    # Build and insert new chunks
    db_chunks = [
        ContractChunk(
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
        for chunk in chunks
    ]
    db.add_all(db_chunks)
    await db.flush()
    logger.info(f"chunks_saved_postgres: count={len(db_chunks)} contract_id={contract_id}")


async def _phase_b_embed_and_index(
    chunks: list,
    contract_id: UUID,
    org_id: UUID,
    vector_store,
) -> None:
    """
    Phase B: bge-m3 embed + Pinecone upsert.
    NO database session held — runs after Phase A committed.
    Long-running (10+ mins on CPU). Safe from DB timeout issues.
    """
    # Delete old Pinecone vectors
    try:
        await vector_store.delete_contract(org_id, contract_id)
    except Exception as e:
        logger.warning(f"pinecone_delete_failed: {e}")

    # Only embed non-signature chunks
    embeddable = [c for c in chunks if c.chunk_type != "signature"]
    if not embeddable:
        logger.info(f"chunk_indexing_complete: total={len(chunks)} embedded=0 contract_id={contract_id}")
        return

    # Run bge-m3 in subprocess — isolates 1.3GB model from Celery worker
    import subprocess, json as _json, sys as _sys, os as _os
    _embed_script = _os.path.join(_os.path.dirname(__file__), "embed_subprocess.py")
    pinecone_vectors = []

    for i in range(0, len(embeddable), EMBED_BATCH_SIZE):
        batch = embeddable[i:i+EMBED_BATCH_SIZE]
        texts = [c.text for c in batch]
        proc = subprocess.run(
            [_sys.executable, _embed_script],
            input=_json.dumps(texts),
            capture_output=True, text=True, timeout=300
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Embedding subprocess failed: {proc.stderr[:200]}")
        embeddings = _json.loads(proc.stdout)

        for chunk, embedding in zip(batch, embeddings):
            pinecone_vectors.append((
                f"chunk_{chunk.chunk_id}",
                embedding,
                {
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
                    "text_preview":  chunk.text[:200],
                }
            ))

    # Upsert to Pinecone
    if pinecone_vectors:
        namespace = f"org_{str(org_id).replace('-','')[:8]}"
        idx = vector_store.index
        for i in range(0, len(pinecone_vectors), PINECONE_BATCH_SIZE):
            batch = pinecone_vectors[i:i+PINECONE_BATCH_SIZE]
            vectors = [{"id": v[0], "values": v[1], "metadata": v[2]} for v in batch]
            idx.upsert(vectors=vectors, namespace=namespace)
            logger.info(f"Upserting {len(batch)} vectors into namespace '{namespace}'")

        logger.info(f"chunks_indexed_pinecone: count={len(pinecone_vectors)} contract_id={contract_id}")

    logger.info(f"chunk_indexing_complete: total={len(chunks)} embedded={len(embeddable)} contract_id={contract_id}")


async def fetch_chunk_texts(
    chunk_ids: list[str],
    db: AsyncSession,
) -> dict[str, str]:
    """Fetch full text for chunk IDs from PostgreSQL."""
    if not chunk_ids:
        return {}
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


async def bm25_search(
    query: str,
    org_id: UUID,
    db: AsyncSession,
    contract_id: Optional[UUID] = None,
    top_k: int = 10,
    exclude_types: list[str] = None,
) -> list[dict]:
    """BM25 full-text search on contract_chunks table."""
    exclude_types = exclude_types or ["signature"]
    exclude_list = ",".join(f"'{t}'" for t in exclude_types)
    conditions = [
        "org_id = :org_id",
        f"chunk_type NOT IN ({exclude_list})",
        "to_tsvector('simple', text) @@ plainto_tsquery('simple', :query)",
    ]
    params = {"org_id": str(org_id), "query": query}
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
    """Fetch chunks referenced by cross_refs of given chunks."""
    if not chunk_ids:
        return []
    clean_ids = [cid.replace("chunk_","") if cid.startswith("chunk_") else cid
                 for cid in chunk_ids]
    placeholders = ",".join(f"'{cid}'" for cid in clean_ids)
    try:
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

        all_refs = []
        contract_id = rows[0][1]
        for row in rows:
            all_refs.extend(row[0] or [])

        if not all_refs:
            return []

        ref_conditions = " OR ".join([
            f"heading ILIKE '%{ref.split()[-1][:20]}%' OR section_ref ILIKE '%{ref.split()[-1][:20]}%'"
            for ref in all_refs[:5]
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
