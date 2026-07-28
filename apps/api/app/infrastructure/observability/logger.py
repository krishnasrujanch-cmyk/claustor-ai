"""
Claustor AI — AI Observability Logger
Fire-and-forget logging of every LLM call to ai_observability table.
"""
import asyncio
import structlog
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


@dataclass
class ObservabilityEvent:
    agent_role:         str
    model:              str
    provider:           str
    prompt_tokens:      int   = 0
    completion_tokens:  int   = 0
    cost_usd:           float = 0.0
    latency_ms:         int   = 0
    retrieval_time_ms:  int   = 0
    first_token_ms:     int   = 0
    hallucination:      bool  = False
    groundedness:       float = None
    confidence:         float = None
    citations_verified: int   = 0
    citations_total:    int   = 0
    chunks_retrieved:   int   = 0
    chunks_used:        int   = 0
    cache_hit:          bool  = False
    safety_passed:      bool  = True
    injection_detected: bool  = False
    judge_triggered:    bool  = False
    user_feedback:      str   = None
    query_preview:      str   = None
    org_id:             str   = None
    user_id:            str   = None
    contract_id:        str   = None


async def log_llm_call(event: ObservabilityEvent) -> None:
    """Fire-and-forget LLM call logging. Never raises."""
    try:
        from sqlalchemy import text
        from app.infrastructure.database.session import async_session_factory

        total = event.prompt_tokens + event.completion_tokens

        async with async_session_factory() as session:
            await session.execute(text("""
                INSERT INTO ai_observability (
                    org_id, user_id, contract_id,
                    agent_role, model, provider,
                    prompt_tokens, completion_tokens, total_tokens, cost_usd,
                    latency_ms, retrieval_time_ms, first_token_ms,
                    hallucination, groundedness, confidence,
                    citations_verified, citations_total,
                    chunks_retrieved, chunks_used, cache_hit,
                    safety_passed, injection_detected, judge_triggered,
                    user_feedback, query_preview
                ) VALUES (
                    :org_id, :user_id, :contract_id,
                    :agent_role, :model, :provider,
                    :prompt_tokens, :completion_tokens, :total_tokens, :cost_usd,
                    :latency_ms, :retrieval_time_ms, :first_token_ms,
                    :hallucination, :groundedness, :confidence,
                    :citations_verified, :citations_total,
                    :chunks_retrieved, :chunks_used, :cache_hit,
                    :safety_passed, :injection_detected, :judge_triggered,
                    :user_feedback, :query_preview
                )
            """), {
                "org_id":            event.org_id,
                "user_id":           event.user_id,
                "contract_id":       event.contract_id,
                "agent_role":        event.agent_role,
                "model":             event.model,
                "provider":          event.provider,
                "prompt_tokens":     event.prompt_tokens,
                "completion_tokens": event.completion_tokens,
                "total_tokens":      total,
                "cost_usd":          event.cost_usd,
                "latency_ms":        event.latency_ms,
                "retrieval_time_ms": event.retrieval_time_ms,
                "first_token_ms":    event.first_token_ms,
                "hallucination":     event.hallucination,
                "groundedness":      event.groundedness,
                "confidence":        event.confidence,
                "citations_verified":event.citations_verified,
                "citations_total":   event.citations_total,
                "chunks_retrieved":  event.chunks_retrieved,
                "chunks_used":       event.chunks_used,
                "cache_hit":         event.cache_hit,
                "safety_passed":     event.safety_passed,
                "injection_detected":event.injection_detected,
                "judge_triggered":   event.judge_triggered,
                "user_feedback":     event.user_feedback,
                "query_preview":     event.query_preview,
            })
            await session.commit()
    except Exception as e:
        logger.warning("observability_log_failed", error=str(e))


def fire_and_forget_log(event: ObservabilityEvent) -> None:
    """Schedule observability log as background task."""
    try:
        asyncio.create_task(log_llm_call(event))
    except RuntimeError:
        pass  # no event loop — skip
