"""
Claustor AI — Chat Endpoints
AI Copilot chat with hybrid search RAG.
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.infrastructure.database.session import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    contract_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None


class CitationOut(BaseModel):
    citation_number: int
    clause_type: str
    page: int
    rrf_score: float
    source: str
    text_preview: str


class ChatOut(BaseModel):
    answer: str
    citations: list[dict]
    contract_id: str | None
    is_safe: bool
    tokens_used: int
    provider: str


class ConversationTurn(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    citations: list | None
    created_at: str

    model_config = {"from_attributes": True}


@router.post("/", response_model=ChatOut)
async def chat(
    req: ChatRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    AI Copilot chat endpoint.

    Features:
    - Hybrid search (semantic + keyword + RRF fusion)
    - Multi-turn conversation history
    - Safety guardrail
    - Citations with source tracking
    - Role-aware responses
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if len(req.query) > 2000:
        raise HTTPException(status_code=400, detail="Query too long. Maximum 2000 characters.")

    from app.agents.rag.chat_agent import get_chat_agent
    agent = get_chat_agent()

    response = await agent.chat(
        query=req.query.strip(),
        org_id=user.org_id,
        user_id=user.id,
        db=db,
        plan=user.plan,
        contract_id=req.contract_id,
        conversation_id=req.conversation_id,
    )

    logger.info(
        "chat_request",
        org_id=str(user.org_id),
        user_id=str(user.id),
        contract_id=str(req.contract_id) if req.contract_id else None,
        query=req.query[:50],
        provider=response.provider,
    )

    return ChatOut(
        answer=response.answer,
        citations=response.citations,
        contract_id=response.contract_id,
        is_safe=response.is_safe,
        tokens_used=response.tokens_used,
        provider=response.provider,
    )


@router.get("/history")
async def get_history(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    contract_id: uuid.UUID | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Get conversation history for a contract."""
    import sqlalchemy
    from app.domain.models import Conversation

    query = sqlalchemy.select(Conversation).where(
        Conversation.org_id == user.org_id,
        Conversation.user_id == user.id,
    )
    if contract_id:
        query = query.where(Conversation.contract_id == contract_id)

    query = query.order_by(Conversation.created_at.desc()).limit(limit)
    result = await db.execute(query)
    conversations = result.scalars().all()

    return {
        "history": [
            {
                "id": str(c.id),
                "role": c.role,
                "content": c.content,
                "citations": c.citations,
                "created_at": c.created_at.isoformat(),
            }
            for c in reversed(list(conversations))
        ],
        "total": len(conversations),
    }


@router.delete("/history")
async def clear_history(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    contract_id: uuid.UUID | None = Query(None),
):
    """Clear conversation history."""
    import sqlalchemy
    from app.domain.models import Conversation

    query = sqlalchemy.delete(Conversation).where(
        Conversation.org_id == user.org_id,
        Conversation.user_id == user.id,
    )
    if contract_id:
        query = query.where(Conversation.contract_id == contract_id)

    await db.execute(query)
    await db.commit()
    return {"status": "cleared"}


@router.post("/feedback")
async def submit_feedback(
    payload: dict,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit feedback on a chat response (👍/👎).
    Used for RLHF and quality improvement.
    """
    import sqlalchemy
    from app.domain.models import Conversation

    conversation_id = payload.get("conversation_id")
    feedback = payload.get("feedback")  # "positive" or "negative"

    if feedback not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="Feedback must be 'positive' or 'negative'")

    result = await db.execute(
        sqlalchemy.select(Conversation).where(
            Conversation.id == uuid.UUID(conversation_id),
            Conversation.org_id == user.org_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Store feedback in citations field (extend later with dedicated table)
    existing = conv.citations or {}
    if isinstance(existing, list):
        existing = {"citations": existing}
    existing["feedback"] = feedback

    await db.execute(
        sqlalchemy.update(Conversation)
        .where(Conversation.id == conv.id)
        .values(citations=existing)
    )
    await db.commit()

    return {"status": "feedback recorded", "feedback": feedback}
