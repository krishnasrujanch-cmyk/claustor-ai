"""Claustor AI — System Endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.session import get_db
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "claustor-ai-api"}


@router.get("/llm-status")
async def llm_status():
    from app.infrastructure.llm.router import get_llm_router
    r = get_llm_router()
    status = await r.get_provider_status()
    return {"providers": status}


@router.post("/test-llm")
async def test_llm():
    from app.infrastructure.llm.router import get_llm_router
    from app.infrastructure.llm.base import LLMMessage, AgentRole
    r = get_llm_router()
    response = await r.complete(
        messages=[
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="Say 'Claustor AI is ready!' and nothing else."),
        ],
        role=AgentRole.ANSWERER,
    )
    return {
        "response": response.content,
        "provider": response.provider.value,
        "model": response.model,
        "tokens": response.total_tokens,
        "cost_usd": round(response.cost_usd, 6),
        "latency_ms": response.latency_ms,
    }


@router.post("/test-pinecone")
async def test_pinecone():
    import uuid
    from app.infrastructure.vector_store.pinecone_store import get_vector_store
    store = get_vector_store()
    test_org = uuid.UUID("00000000-0000-0000-0000-000000000001")
    contract_id = uuid.uuid4()
    chunks = [
        {"text": "This is a test clause for Claustor AI.", "chunk_index": 0},
        {"text": "Liability shall be limited to the contract value.", "chunk_index": 1},
    ]
    upserted = await store.upsert_contract(test_org, contract_id, chunks)
    results = await store.search(test_org, "What is the liability?", top_k=2, contract_id=contract_id)
    await store.delete_contract(test_org, contract_id)
    return {
        "status": "ok",
        "vectors_upserted": upserted,
        "search_results": len(results),
        "top_score": results[0]["score"] if results else 0,
    }


@router.post("/process-contract")
async def process_contract_inline(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Trigger contract processing inline (dev only — no Celery needed)."""
    from uuid import UUID
    import sqlalchemy
    from app.agents.pipeline.contract_pipeline import ContractPipeline
    from app.domain.models import Contract

    contract_id = UUID(payload["contract_id"])

    # Get contract
    result = await db.execute(
        sqlalchemy.select(Contract).where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Download file from GCS or use local fallback
    try:
        from app.infrastructure.storage.gcs import get_storage_client
        storage = get_storage_client()
        file_bytes = await storage.download_contract(contract.org_id, contract_id)
    except Exception:
        # GCS not configured locally — read from upload path
        raise HTTPException(
            status_code=400,
            detail="GCS not configured. File not available for processing."
        )

    pipeline = ContractPipeline()
    await pipeline.process(
        contract_id=contract_id,
        org_id=contract.org_id,
        file_hash=contract.file_hash,
        db=db,
    )
    return {"status": "processed", "contract_id": str(contract_id)}


@router.post("/process-local")
async def process_local(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Process contract from local file path (dev only)."""
    from uuid import UUID
    import sqlalchemy
    from app.agents.pipeline.contract_pipeline import ContractPipeline
    from app.domain.models import Contract

    contract_id = UUID(payload["contract_id"])
    file_path = payload["file_path"]

    result = await db.execute(
        sqlalchemy.select(Contract).where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Read file from local disk
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # Override download in pipeline by patching temporarily
    pipeline = ContractPipeline()

    # Monkey-patch _download_file for local dev
    async def _local_download(org_id, contract_id, file_hash):
        return file_bytes
    pipeline._download_file = _local_download

    await pipeline.process(
        contract_id=contract_id,
        org_id=contract.org_id,
        file_hash=contract.file_hash,
        db=db,
    )

    return {"status": "processed", "contract_id": str(contract_id)}
