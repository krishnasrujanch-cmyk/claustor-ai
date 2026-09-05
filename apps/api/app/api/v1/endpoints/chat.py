"""
Claustor AI — Chat Endpoints
AI Copilot chat with hybrid search RAG.
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter
from fastapi import Depends, HTTPException, Query
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
        logger.warning(f"query_counter_failed: {e}")

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

            # ── Smart Query Routing (Judge + Guardrails + Reranker) ──
            from app.infrastructure.security.sanitizer import validate_context_window
            from app.domain.models import Conversation as _StreamConv
            from sqlalchemy import select as _ssel, desc as _sdesc
            from app.agents.rag.structured_query import (
                run_structured_query, run_missing_clause_query)
            from app.agents.rag.judge_router import judge_classify
            from app.agents.rag.guardrails import (
                check_prompt_injection, check_and_sanitize_pii,
                validate_token_limit, build_response_schema_instruction)

            raw_query = req.query.strip()

            # ── Guardrail 1: Prompt Injection Detection ──
            _injection_check = check_prompt_injection(raw_query)
            if not _injection_check.passed:
                yield "data: " + json.dumps({"type":"error","message":_injection_check.blocked_reason}) + "\n\n"
                return

            # ── Guardrail 2: PII Detection + Sanitization ──
            _pii_check = check_and_sanitize_pii(raw_query)
            if _pii_check.sanitized_query:
                raw_query = _pii_check.sanitized_query
            if _pii_check.pii_detected:
                logger.warning(f"pii_sanitized: types={_pii_check.pii_detected}")

            # ── Step 1: Load Conversation History ──
            _hist_rows = []
            _last_assistant = ""
            _scoped_contract_id = req.contract_id
            try:
                _hist_r = await db.execute(
                    _ssel(_StreamConv.role, _StreamConv.content, _StreamConv.contract_id)
                    .where(_StreamConv.org_id == user.org_id,
                           _StreamConv.user_id == user.id)
                    .order_by(_sdesc(_StreamConv.created_at))
                    .limit(6)
                )
                _hist_rows = _hist_r.fetchall()
                for _t in _hist_rows:
                    if _t[0] == "assistant":
                        # Only use history from same contract scope
                        same_scope = (req.contract_id is None and _t[2] is None) or                                      (req.contract_id is not None and str(_t[2]) == str(req.contract_id))
                        if same_scope:
                            _last_assistant = _t[1][:400]
                        # For vague follow-ups, scope to previous contract
                        _vague_words = ["name","title","which","what contract","this contract",
                                        "share more","tell me more","elaborate","details","it","this"]
                        _is_vague = any(w in req.query.lower() for w in _vague_words) and len(req.query.split()) < 8
                        if _t[2] and not req.contract_id and _is_vague:
                            _scoped_contract_id = _t[2]
                        break
            except Exception:
                pass

            # ── Step 2: JUDGE — Intent + Entity + Query Rewrite ──
            # Get contract meta for Judge context (party resolution)
            _judge_meta = {}
            if req.contract_id:
                try:
                    from sqlalchemy import select as _smeta, text as _tmeta
                    _crow = await db.execute(_tmeta("""
                        SELECT title, contract_type, counterparty
                        FROM contracts WHERE id = :cid
                    """), {"cid": str(req.contract_id)})
                    _cr = _crow.fetchone()
                    if _cr:
                        _judge_meta = {"title": _cr[0], "contract_type": _cr[1], "counterparty": _cr[2]}
                except Exception:
                    pass
            judge = await judge_classify(
                query=raw_query,
                llm=agent.llm,
                history_turns=[(r[0], r[1]) for r in _hist_rows],
                org_id=user.org_id,
                contract_meta=_judge_meta,
            )

            # Use Judge's rewritten query for better vector retrieval
            retrieval_query = judge.rewritten_query or raw_query
            # Only prepend last assistant for truly vague followups (< 5 words)
            if judge.is_followup and _last_assistant and len(raw_query.split()) < 5:
                retrieval_query = _last_assistant[:200] + " " + raw_query

            # Extract date range from filters
            _date_start = judge.filters.pop("date_start", None)
            _date_end   = judge.filters.pop("date_end", None)

            # ── Step 3: DB Query (if needed) ──
            extra_context = ""
            if judge.needs_db:
                if judge.intent == "missing" or judge.filters.get("missing_clause"):
                    extra_context = await run_missing_clause_query(
                        query=raw_query, org_id=user.org_id, db=db)
                else:
                    extra_context = await run_structured_query(
                        intent_sub_type=judge.db_query_type,
                        date_start=_date_start,
                        date_end=_date_end,
                        timeframe=None,
                        query=raw_query,
                        org_id=user.org_id,
                        db=db,
                        contract_id=_scoped_contract_id,
                        filters=judge.filters,
                    )

            # Heartbeat before slow bge-m3 encoding
            yield "data: " + __import__("json").dumps({"type":"heartbeat"}) + "\n\n"


            # ── Step 4: Vector Search + Reranker (if needed) ──
            if judge.needs_vector:
                context = await agent.retriever.retrieve(
                    query=retrieval_query,
                    org_id=user.org_id,
                    db=db,
                    plan=user.plan,
                    contract_id=_scoped_contract_id,
                    raw_query=raw_query,
                )
                try:
                    from app.agents.rag.reranker import rerank_chunks
                    if hasattr(context, "chunks") and context.chunks:
                        context.chunks = rerank_chunks(raw_query, context.chunks, top_k=6)
                except Exception:
                    pass
            else:
                class _EmptyCtx:
                    context_text = ""
                    chunks = []
                context = _EmptyCtx()

            # ── Step 5: Combine Context + Response Schema ──
            response_schema = build_response_schema_instruction(judge.intent)
            db_instruction = (f"\n\nINSTRUCTION: {response_schema}") if extra_context else ""
            combined = (context.context_text or "") + extra_context + db_instruction
            safe_ctx, _ = validate_context_window(combined, max_tokens=80000)

            # Build messages
            # Load profile context for guided analysis
            _profile_ctx = ""
            try:
                from app.agents.profiles.profile_loader import build_analysis_context
                _profile_ctx = build_analysis_context(
                    contract_type=getattr(judge, 'contract_type', None) or 'Other',
                    industry='general',
                    role='neutral',
                )
            except Exception:
                pass

            messages = agent._build_messages(
                query=req.query.strip(),
                context=safe_ctx,
                history=[],
                summary=None,
                review_status=None,
                review_notes=None,
                profile_context=_profile_ctx,
            )

            # Step 2: Stream tokens from Groq
            from app.infrastructure.llm.base import AgentRole
            from app.infrastructure.llm.router import get_llm_router
            router_llm = get_llm_router()

            full_answer = ""
            # Use non-streaming for now, emit word by word for UX
            # (True streaming requires AsyncIterator support in provider)
            # Complexity-based model routing
            from app.core.plan_model_routing import get_answerer_for_complexity
            _complexity = getattr(judge, "complexity", "simple") if judge else "simple"
            _answerer_cfg = get_answerer_for_complexity(user.plan, _complexity)
            logger.info("stream_answerer_routing",
                        plan=user.plan, complexity=_complexity,
                        provider=_answerer_cfg["provider"], model=_answerer_cfg["model"])
            # Check if broad query — use structured pipeline
            _broad_signals = ["key risk", "payment due", "summary", "overview",
                              "main risk", "important clause", "all risk",
                              "critical issue", "comprehensive", "analyse",
                              "analyze", "obligations and risk"]
            _is_broad = any(s in req.query.lower() for s in _broad_signals)

            if _is_broad and hasattr(context, "chunks") and context.chunks and len(context.chunks) >= 3:
                logger.info("structured_pipeline_stream", query=req.query[:50])
                from app.agents.rag.structured_synthesizer import get_structured_synthesizer
                _synth = get_structured_synthesizer()
                full_answer = await _synth.synthesize(
                    query=req.query.strip(),
                    chunks=context.chunks,
                    citations=[],
                )
                # Create minimal response object for downstream meta emission
                class _StructuredResponse:
                    total_tokens = 0
                    cost_usd = 0.0
                    extra = {}
                response = _StructuredResponse()
            else:
                response = await router_llm.complete(
                    messages=messages,
                    role=AgentRole.ANSWERER,
                    json_mode=False,
                    preferred_provider=_answerer_cfg["provider"],
                    preferred_model=_answerer_cfg["model"],
                )
                full_answer = response.content
            # Grounding validation
            try:
                from app.agents.profiles.grounding_validator import validate_grounding, add_grounding_disclaimer
                _grd = validate_grounding(full_answer, safe_ctx)
                if not _grd.is_reliable:
                    full_answer = add_grounding_disclaimer(full_answer, _grd)
                    logger.warning("grounding_low_stream", score=_grd.score)
            except Exception:
                pass

            # Emit tokens word by word with small delay for UX
            import asyncio
            words = full_answer.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words)-1 else "")
                yield "data: " + json.dumps({"type":"token","content":chunk}) + "\n\n"

                if i % 5 == 0:  # small pause every 5 words
                    await asyncio.sleep(0.01)

            # Step 3: Citations + hallucination check
            chunks = context.chunks if hasattr(context, "chunks") else []
            # Convert HybridSearchResult objects to dicts
            chunk_dicts = []
            for ci, ch in enumerate(chunks):
                if isinstance(ch, dict):
                    d = dict(ch)
                elif hasattr(ch, "to_dict"):
                    d = ch.to_dict()
                else:
                    d = {"index": ci+1, "chunk_index": ci+1,
                         "clause_type": getattr(ch,"clause_type","") or "",
                         "text": getattr(ch,"text","") or "", "id": ci+1}
                d.setdefault("index", ci+1)
                chunk_dicts.append(d)
            # Skip hallucination check for DB-only responses
            if not chunk_dicts and extra_context:
                from app.infrastructure.security.hallucination import HallucinationCheckResult
                halluc = HallucinationCheckResult(answer=full_answer, total_citations=0,
                    verified_citations=0, groundedness=1.0, is_hallucinated=False,
                    needs_regeneration=False)
            else:
                halluc = verify_citations(full_answer, chunk_dicts)
            chunks = chunk_dicts

            # Extract citations from answer
            import re
            cited = sorted(set(int(m) for m in re.findall(r"\[(\d+)\]", full_answer)))
            citations = []
            for idx in cited:
                if idx <= len(chunks):
                    c = chunks[idx-1] if idx-1 < len(chunks) else {}
                    citations.append({
                        "index":       idx,
                        "clause_type": c.get("clause_type",""),
                        "text":        c.get("text","")[:200],
                    })

            yield "data: " + json.dumps({"type":"citations","citations":citations}) + "\n\n"

            yield "data: " + json.dumps({"type":"meta","groundedness":round(halluc.groundedness,3),"confidence":response.extra.get("confidence",None),"tokens":response.total_tokens,"cost":round(response.cost_usd,6),"chunks_retrieved":len(chunks),"context_chars":sum(len(c.text if hasattr(c,"text") else c.get("text","")) for c in chunks if c),"db_sourced":judge.needs_db}) + "\n\n"

            yield "data: " + json.dumps({"type":"done"}) + "\n\n"


            # ── Observability logging ─────────────────────
            try:
                from app.infrastructure.observability.logger import (
                    ObservabilityEvent, fire_and_forget_log)
                fire_and_forget_log(ObservabilityEvent(
                    agent_role="answerer", model=response.model,
                    provider=str(response.provider),
                    prompt_tokens=response.input_tokens,
                    completion_tokens=response.output_tokens,
                    cost_usd=response.cost_usd, latency_ms=response.latency_ms,
                    hallucination=halluc.is_hallucinated,
                    groundedness=halluc.groundedness,
                    citations_verified=halluc.verified_citations,
                    citations_total=halluc.total_citations,
                    chunks_retrieved=len(chunks), chunks_used=len(citations),
                    safety_passed=True, org_id=str(user.org_id),
                    user_id=str(user.id),
                    contract_id=str(req.contract_id) if req.contract_id else None,
                    query_preview=req.query[:200],
                ))
            except Exception:
                pass

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
            import traceback
            logger.error(f"stream_error: {e}\n{traceback.format_exc()}")
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


@router.get("/suggested-prompts")
async def get_suggested_prompts(
    contract_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Generate dynamic prompts based on contract type and industry."""
    from app.infrastructure.llm.base import AgentRole, LLMMessage
    from app.agents.rag.chat_agent import ChatAgent

    contract_meta = {}
    if contract_id:
        from app.domain.models import Contract as _C
        from sqlalchemy import select as _s
        r = await db.execute(
            _s(_C.contract_type, _C.risk_level, _C.governing_law,
               _C.counterparty, _C.summary)
            .where(_C.id == contract_id, _C.org_id == user.org_id)
        )
        row = r.fetchone()
        if row:
            contract_meta = {
                "contract_type": row[0], "risk_level": row[1],
                "governing_law": row[2], "counterparty": row[3],
                "summary": row[4],
            }

    prompt = f"""Generate 4 categories of questions for a contract analyst.
Contract context: {contract_meta if contract_meta else "General contract portfolio"}

Return JSON:
{{
  "tabs": [
    {{
      "key": "risk",
      "label": "Risk",
      "prompts": [
        {{"question": "...", "subtitle": "..."}}
      ]
    }},
    {{
      "key": "financial",
      "label": "Financial",
      "prompts": [...]
    }},
    {{
      "key": "legal",
      "label": "Legal",
      "prompts": [...]
    }},
    {{
      "key": "obligations",
      "label": "Obligations",
      "prompts": [...]
    }}
  ]
}}
4 prompts per tab. Make them specific to the contract type: {contract_meta.get('contract_type','general')}.
Return ONLY valid JSON."""

    try:
        agent = ChatAgent()
        response = await agent.llm.complete(
            messages=[
                LLMMessage(role="system", content="Return only valid JSON."),
                LLMMessage(role="user", content=prompt),
            ],
            role=AgentRole.EXTRACTOR,
            json_mode=True,
        )
        import json as _j
        return _j.loads(response.content.strip())
    except Exception as e:
        logger.warning(f"suggested_prompts_failed: {e}")
        # Return defaults
        return {"tabs": []}
