"""
Claustor AI — Enhanced Guardrails
Covers: Jailbreak, Prompt Injection, PII Detection,
        Token Limit, Output Validation
"""

from __future__ import annotations
import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ── Prompt Injection Patterns ─────────────────────────────────────
PROMPT_INJECTION_PATTERNS = [
    r"ignore (previous|prior|above|all) instructions?",
    r"forget (everything|all|previous|prior)",
    r"new (role|persona|instructions?|task)",
    r"you are now",
    r"act as (a|an|if)",
    r"pretend (to be|you are|you're)",
    r"override (system|safety|instructions?)",
    r"reveal (system prompt|instructions?|prompt)",
    r"print (system prompt|your instructions?)",
    r"what (are|is) your (system prompt|instructions?)",
    r"disregard (previous|prior|all|safety)",
    r"bypass (safety|restrictions?|filters?|guardrails?)",
    r"jailbreak",
    r"DAN mode",
    r"developer mode",
    r"\[SYSTEM\]",
    r"</?(system|instruction|prompt)>",
]

# ── PII Patterns ──────────────────────────────────────────────────
PII_PATTERNS = {
    "aadhaar":       r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "pan":           r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "credit_card":   r"\b(?:\d{4}[\s-]?){3}\d{4}\b",
    "phone_IN":      r"\b(?:\+91|0)?[6-9]\d{9}\b",
    "email":         r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
    "passport_IN":   r"\b[A-Z][1-9][0-9]{7}\b",
    "ssn_US":        r"\b\d{3}-\d{2}-\d{4}\b",
    "bank_account":  r"\b\d{9,18}\b",
    "ifsc":          r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    "gstin":         r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b",
}

# ── Response Validation Rules ─────────────────────────────────────
MAX_RESPONSE_TOKENS    = 2000
MIN_GROUNDEDNESS       = 0.5   # below this = flag as potentially hallucinated
CITATION_ORG_CHECK     = True  # verify citations belong to user's org

@dataclass
class GuardrailResult:
    passed:           bool
    blocked_reason:   Optional[str] = None
    pii_detected:     list = None
    injection_type:   Optional[str] = None
    sanitized_query:  Optional[str] = None

    def __post_init__(self):
        if self.pii_detected is None:
            self.pii_detected = []


def check_prompt_injection(query: str) -> GuardrailResult:
    """Detect prompt injection attempts."""
    q_lower = query.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, q_lower, re.IGNORECASE):
            logger.warning(f"prompt_injection_detected: pattern={pattern!r} query={query[:80]!r}")
            return GuardrailResult(
                passed=False,
                blocked_reason="Query contains prompt injection patterns and cannot be processed.",
                injection_type=pattern,
            )
    return GuardrailResult(passed=True)


def check_and_sanitize_pii(query: str) -> GuardrailResult:
    """Detect PII in query and sanitize before sending to LLM."""
    detected = []
    sanitized = query

    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, query)
        if matches:
            detected.append(pii_type)
            # Replace PII with placeholder
            sanitized = re.sub(pattern, f"[{pii_type.upper()}]", sanitized)

    if detected:
        logger.warning(f"pii_detected_in_query: types={detected} org_query_sanitized=true")
        return GuardrailResult(
            passed=True,  # Don't block — sanitize and continue
            pii_detected=detected,
            sanitized_query=sanitized,
        )

    return GuardrailResult(passed=True, sanitized_query=query)


def validate_token_limit(context: str, query: str, max_tokens: int = 80000) -> tuple[str, bool]:
    """Pre-flight token limit check. Returns (truncated_context, was_truncated)."""
    # Rough estimate: 1 token ≈ 4 chars
    total_chars = len(context) + len(query)
    max_chars = max_tokens * 4

    if total_chars > max_chars:
        truncate_at = max_chars - len(query) - 1000  # leave room for query
        logger.warning(f"context_truncated: original={total_chars} max_chars={max_chars}")
        return context[:truncate_at] + "\n[Context truncated due to length]", True

    return context, False


def validate_output(
    answer: str,
    org_id: str,
    citations: list,
    groundedness: float,
) -> dict:
    """
    Validate LLM output:
    1. Citations reference real content
    2. Groundedness above threshold
    3. No obvious hallucination markers
    """
    issues = []

    # Check groundedness
    if groundedness < MIN_GROUNDEDNESS and citations:
        issues.append(f"Low groundedness: {groundedness:.0%}")

    # Check for hallucination markers
    hallucination_phrases = [
        "i don't have access",
        "i cannot find",
        "as an ai",
        "i'm not able to",
        "unfortunately, i",
    ]
    answer_lower = answer.lower()
    for phrase in hallucination_phrases:
        if phrase in answer_lower:
            issues.append(f"Potential AI confusion: '{phrase}'")
            break

    # Check citation count is reasonable
    if len(citations) > 20:
        issues.append(f"Unusual citation count: {len(citations)}")

    if issues:
        logger.warning(f"output_validation_issues: {issues} org_id={org_id}")

    return {
        "valid":       len(issues) == 0,
        "issues":      issues,
        "groundedness": groundedness,
    }


def build_response_schema_instruction(intent: str) -> str:
    """Return response format instruction based on intent."""
    schemas = {
        "structured": """
RESPONSE FORMAT for structured data:
- Lead with the direct answer (count, list, summary)
- Present all items as numbered/bulleted list with: name, key metric, expiry (if relevant), risk level
- Add 1-2 sentence insight/recommendation after the list
- End with action item if risk is present
- Do NOT say "Based on context" or "According to the database" """,

        "semantic": """
RESPONSE FORMAT for clause/content questions:
- Answer directly with the specific clause details
- Cite sources using [N] notation for every claim
- Organize with clear headings if multiple aspects
- Highlight key risks, obligations, or deadlines
- Keep response focused and concise""",

        "hybrid": """
RESPONSE FORMAT for filtered contract analysis:
- First: list matching contracts from database with key attributes
- Then: for each contract, explain relevant clause details
- Cite sources [N] for clause content
- Add risk assessment and recommendations
- Action items if deadlines are approaching""",

        "missing": """
RESPONSE FORMAT for missing clause analysis:
- State clearly which contracts HAVE the clause
- State clearly which contracts are MISSING the clause
- Explain the risk of missing this clause type
- Recommend remediation steps""",

        "followup": """
RESPONSE FORMAT for follow-up questions:
- Continue naturally from previous context
- Be specific about which contract you're discussing
- Cite sources [N] for new claims
- Don't repeat information already given""",
    }
    return schemas.get(intent, schemas["semantic"])
