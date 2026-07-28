"""
Claustor AI — Judge LLM
Verifies high-risk clause analysis using Claude Sonnet.

Triggered when:
  - risk_score > 75
  - confidence < 0.60
  - Enterprise plan (always)

Returns:
  - Verified clause type
  - Adjusted risk score
  - Confidence 0-100
  - Corrections if any
  - Reasoning
"""
import json
import structlog
from dataclasses import dataclass, field
from typing import Optional

logger = structlog.get_logger(__name__)

JUDGE_TRIGGER_RISK_SCORE = 75
JUDGE_TRIGGER_CONFIDENCE = 0.60

JUDGE_SYSTEM_PROMPT = """You are an expert legal contract analyst and AI output verifier.
Your role is to verify clause analysis produced by a fast AI model.

You will receive:
1. The original clause text
2. The fast AI model's analysis (type, risk score, reasoning)

Your task:
- Verify if the clause type classification is correct
- Verify if the risk score (0-100) is appropriate
- Check if the reasoning is sound and grounded in the clause text
- Provide your own confidence score

Be strict but fair. Legal accuracy is critical.

Return ONLY valid JSON, no other text:
{
  "verified_type": "string — confirmed or corrected clause type",
  "verified_risk_score": "integer 0-100",
  "confidence": "float 0-1 — your confidence in this analysis",
  "type_correct": "boolean — was original type correct",
  "score_correct": "boolean — was original score within 10 points",
  "corrections": "string — what was wrong, or empty string if nothing",
  "reasoning": "string — brief explanation of your assessment",
  "critical_issues": ["list of specific legal risks found"]
}"""

JUDGE_USER_TEMPLATE = """CLAUSE TEXT:
{clause_text}

ORIGINAL ANALYSIS:
- Clause Type: {clause_type}
- Risk Score: {risk_score}/100
- Risk Level: {risk_level}
- Reasoning: {reasoning}
- Playbook Match: {playbook_match}%
- Deviation: {deviation}

Please verify this analysis."""


@dataclass
class JudgeResult:
    original_type: str
    original_score: int
    verified_type: str
    verified_score: int
    confidence: float
    type_correct: bool
    score_correct: bool
    corrections: str
    reasoning: str
    critical_issues: list = field(default_factory=list)
    judge_triggered: bool = True
    cost_usd: float = 0.0


async def judge_clause(
    clause_text: str,
    clause_type: str,
    risk_score: int,
    risk_level: str,
    reasoning: str = "",
    playbook_match: float = 0.0,
    deviation: str = "",
    plan: str = "professional",
    org_id: str = "",
) -> Optional[JudgeResult]:
    """
    Call Claude Sonnet to verify high-risk clause analysis.
    Returns None if judge not triggered (risk too low, free plan).
    """
    # Trigger conditions
    should_judge = (
        risk_score > JUDGE_TRIGGER_RISK_SCORE
        or plan == "enterprise"
    )
    if not should_judge:
        return None

    try:
        from app.infrastructure.llm.router import get_llm_router
        from app.infrastructure.llm.base import LLMMessage, AgentRole

        router = get_llm_router()

        messages = [
            LLMMessage(role="system", content=JUDGE_SYSTEM_PROMPT),
            LLMMessage(role="user", content=JUDGE_USER_TEMPLATE.format(
                clause_text=clause_text[:3000],  # cap to avoid token explosion
                clause_type=clause_type,
                risk_score=risk_score,
                risk_level=risk_level,
                reasoning=reasoning[:500],
                playbook_match=round(playbook_match or 0, 1),
                deviation=deviation or "Not specified",
            )),
        ]

        response = await router.complete(
            messages=messages,
            role=AgentRole.JUDGE,
            temperature=0.0,
            max_tokens=1000,
            json_mode=True,
        )

        raw = response.content.strip()
        data = json.loads(raw)

        result = JudgeResult(
            original_type=clause_type,
            original_score=risk_score,
            verified_type=data.get("verified_type", clause_type),
            verified_score=int(data.get("verified_risk_score", risk_score)),
            confidence=float(data.get("confidence", 0.8)),
            type_correct=bool(data.get("type_correct", True)),
            score_correct=bool(data.get("score_correct", True)),
            corrections=str(data.get("corrections", "")),
            reasoning=str(data.get("reasoning", "")),
            critical_issues=list(data.get("critical_issues", [])),
            judge_triggered=True,
            cost_usd=response.cost_usd,
        )

        logger.info(
            "judge_completed",
            org_id=org_id,
            clause_type=clause_type,
            original_score=risk_score,
            verified_score=result.verified_score,
            confidence=result.confidence,
            type_correct=result.type_correct,
            score_correct=result.score_correct,
            cost_usd=round(response.cost_usd, 6),
        )
        return result

    except Exception as e:
        logger.error("judge_failed", error=str(e), clause_type=clause_type,
                     risk_score=risk_score)
        return None


def apply_judge_result(clause_data: dict, judge: JudgeResult) -> dict:
    """Apply judge corrections to clause data dict."""
    clause_data["judge_triggered"]   = True
    clause_data["judge_confidence"]  = judge.confidence
    clause_data["judge_corrections"] = judge.corrections

    # Apply verified values if they differ significantly
    if not judge.type_correct:
        clause_data["clause_type"] = judge.verified_type
        logger.info("judge_corrected_type",
            original=judge.original_type, corrected=judge.verified_type)

    score_diff = abs(judge.verified_score - judge.original_score)
    if score_diff > 10:
        clause_data["risk_score"] = judge.verified_score
        clause_data["risk_level"] = (
            "high"   if judge.verified_score >= 75 else
            "medium" if judge.verified_score >= 40 else "low"
        )
        logger.info("judge_corrected_score",
            original=judge.original_score, corrected=judge.verified_score)

    if judge.critical_issues:
        clause_data["critical_issues"] = judge.critical_issues

    return clause_data
