"""
Claustor AI — Chat Endpoints
AI Copilot chat with hybrid search RAG.
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
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

    # Increment query usage counter using fresh session
    try:
        from sqlalchemy import update, text
        from app.infrastructure.database.session import async_session_factory
        if async_session_factory:
            async with async_session_factory() as counter_db:
                await counter_db.execute(
                    text("UPDATE organisations SET queries_used = queries_used + 1 WHERE id = :org_id"),
                    {"org_id": str(user.org_id)}
                )
                await counter_db.commit()
    except Exception as e:
        logger.warning("query_counter_failed", error=str(e))

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


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    AI Copilot streaming chat endpoint.
    Returns Server-Sent Events (SSE) — tokens stream as generated.

    Event format:
      data: {"type": "token", "content": "..."}
      data: {"type": "citations", "citations": [...]}
      data: {"type": "meta", "groundedness": 0.97, "confidence": 0.94}
      data: {"type": "done"}
      data: {"type": "error", "message": "..."}
    """
    import json
    from app.agents.rag.chat_agent import get_chat_agent
    from app.infrastructure.security.sanitizer import check_query_for_jailbreak
    from app.infrastructure.security.hallucination import verify_citations

    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if len(req.query) > 2000:
        raise HTTPException(status_code=400, detail="Query too long.")

    async def event_generator():
        try:
            # Step 0: Jailbreak check (fast, local)
            jailbreak = check_query_for_jailbreak(
                req.query, org_id=str(user.org_id), user_id=str(user.id))
            if not jailbreak.is_clean:
                yield "data: " + json.dumps({"type":"error","message":"Query blocked by security filter."}) + "\n\n"
                return

            # Step 1: Safety + retrieval (non-streaming portion)
            agent = get_chat_agent()

            # Get context via normal retrieval
            from app.infrastructure.security.sanitizer import validate_context_window
            context = await agent.retriever.retrieve(
                query=req.query.strip(),
                org_id=user.org_id,
                db=db,
                plan=user.plan,
                contract_id=req.contract_id,
            )

            # Validate context window
            safe_ctx, _ = validate_context_window(context.context_text, max_tokens=80000)

            # Build messages
            messages = agent._build_messages(
                query=req.query.strip(),
                context=safe_ctx,
                history=[],
                summary=None,
                review_status=None,
                review_notes=None,
            )

            # Step 2: Stream tokens from Groq
            from app.infrastructure.llm.base import AgentRole
            from app.infrastructure.llm.router import get_llm_router
            router_llm = get_llm_router()

            full_answer = ""
            # Use non-streaming for now, emit word by word for UX
            # (True streaming requires AsyncIterator support in provider)
            response = await router_llm.complete(
                messages=messages,
                role=AgentRole.ANSWERER,
                json_mode=False,
            )
            full_answer = response.content

            # Emit tokens word by word with small delay for UX
            import asyncio
            words = full_answer.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words)-1 else "")
                yield "data: " + json.dumps({"type":"token","content":chunk}) + "\n\n"
                if i % 5 == 0:  # small pause every 5 words
                    await asyncio.sleep(0.01)

            # Step 3: Citations + hallucination check
            # Convert chunks to dicts + verify citations
            chunk_dicts = []
            raw_chunks = context.chunks if hasattr(context, "chunks") else []
            for ci, ch in enumerate(raw_chunks):
                if hasattr(ch, "to_dict"):
                    d = ch.to_dict()
                elif hasattr(ch, "clause_type"):
                    d = {"clause_type": ch.clause_type, "text": ch.text}
                else:
                    d = ch if isinstance(ch, dict) else {}
                d["index"] = ci + 1
                chunk_dicts.append(d)
            halluc = verify_citations(full_answer, chunk_dicts)

            # Extract citations
            import re
            cited = sorted(set(int(m) for m in re.findall(r"\[(\d+)\]", full_answer)))
            citations = []
            for idx in cited:
                if idx <= len(chunk_dicts):
                    c = chunk_dicts[idx-1]
                    citations.append({
                        "index":       idx,
                        "clause_type": c.get("clause_type",""),
                        "text":        c.get("text","")[:200],
                    })

            yield "data: " + json.dumps({"type":"citations","citations":citations}) + "\n\n"
            _meta = json.dumps({"type":"meta","groundedness":round(halluc.groundedness,3),"confidence":response.extra.get("confidence",None),"tokens":response.total_tokens,"cost":round(response.cost_usd,6)})
            yield "data: " + _meta + "\n\n"
            yield "data: " + json.dumps({"type":"done"}) + "\n\n"

            # Increment usage counter
            try:
                from sqlalchemy import text as _text
                from app.infrastructure.database.session import async_session_factory
                if async_session_factory:
                    async with async_session_factory() as cdb:
                        await cdb.execute(
                            _text("UPDATE organisations SET queries_used = queries_used + 1 WHERE id = :oid"),
                            {"oid": str(user.org_id)}
                        )
                        await cdb.commit()
            except Exception:
                pass

        except Exception as e:
            logger.error("stream_error", error=str(e))
            yield "data: " + json.dumps({"type":"error","message":str(e)}) + "\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )
