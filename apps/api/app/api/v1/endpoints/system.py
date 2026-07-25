"""
Claustor AI — System Endpoints
Health check, LLM provider status, system info.
"""

from fastapi import APIRouter
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/health")
async def health():
    """Basic health check — no auth required."""
    return {"status": "healthy", "service": "claustor-ai-api"}


@router.get("/llm-status")
async def llm_status():
    """Check LLM provider availability and circuit status."""
    from app.infrastructure.llm.router import get_llm_router
    router_instance = get_llm_router()
    status = await router_instance.get_provider_status()
    return {
        "providers": status,
        "available": [p for p in status if status[p]["available"]],
    }


@router.post("/test-llm")
async def test_llm():
    """Test LLM router with a simple prompt."""
    from app.infrastructure.llm.router import get_llm_router
    from app.infrastructure.llm.base import LLMMessage, AgentRole

    router_instance = get_llm_router()
    response = await router_instance.complete(
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
    """Test Pinecone connection and basic upsert + search."""
    import uuid
    from app.infrastructure.vector_store.pinecone_store import get_vector_store

    store = get_vector_store()
    test_org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    contract_id = uuid.uuid4()

    chunks = [
        {"text": "This is a test clause for Claustor AI.", "chunk_index": 0},
        {"text": "Liability shall be limited to the contract value.", "chunk_index": 1},
    ]

    upserted = await store.upsert_contract(test_org_id, contract_id, chunks)
    results = await store.search(test_org_id, "What is the liability?", top_k=2, contract_id=contract_id)
    await store.delete_contract(test_org_id, contract_id)

    return {
        "status": "ok",
        "vectors_upserted": upserted,
        "search_results": len(results),
        "top_score": results[0]["score"] if results else 0,
    }
