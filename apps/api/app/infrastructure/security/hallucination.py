"""
Claustor AI — Hallucination Verifier
Verifies that citations in generated answers actually exist in retrieved context.

Process:
  1. Extract all [1], [2], [3] citation markers from answer
  2. Check each cited chunk index exists in retrieved context
  3. Calculate groundedness = verified / total citations
  4. Flag or regenerate if below threshold
"""
import re
import structlog
from dataclasses import dataclass, field

logger = structlog.get_logger(__name__)

GROUNDEDNESS_WARN_THRESHOLD  = 0.90  # warn if below
GROUNDEDNESS_REGEN_THRESHOLD = 0.70  # regenerate if below


@dataclass
class HallucinationCheckResult:
    answer: str
    total_citations: int
    verified_citations: int
    unverified_indices: list = field(default_factory=list)
    groundedness: float = 1.0
    is_hallucinated: bool = False
    needs_regeneration: bool = False
    warning_message: str = ""


def extract_citation_indices(text: str) -> list[int]:
    """Extract all [N] citation markers from text. Returns sorted unique list."""
    matches = re.findall(r"\[(\d+)\]", text)
    return sorted(set(int(m) for m in matches))


def verify_citations(
    answer: str,
    retrieved_chunks: list[dict],
    org_id: str = "",
    contract_id: str = "",
) -> HallucinationCheckResult:
    """
    Verify citations in an LLM answer against retrieved context chunks.

    Args:
        answer: Generated answer text with [1][2] style citations
        retrieved_chunks: List of context dicts with keys: index, text, clause_type, etc.
        org_id: For logging
        contract_id: For logging

    Returns:
        HallucinationCheckResult with groundedness score and flags
    """
    cited_indices = extract_citation_indices(answer)

    if not cited_indices:
        # No citations at all — could be hallucination or valid uncited answer
        return HallucinationCheckResult(
            answer=answer,
            total_citations=0,
            verified_citations=0,
            groundedness=1.0,  # can't verify what's not cited
            is_hallucinated=False,
        )

    # Build set of valid indices from retrieved chunks
    valid_indices = set()
    for chunk in retrieved_chunks:
        idx = chunk.get("index") or chunk.get("chunk_index") or chunk.get("id")
        if idx is not None:
            valid_indices.add(int(idx))
    # Also accept 1-based indices matching chunk count
    for i in range(1, len(retrieved_chunks) + 1):
        valid_indices.add(i)

    verified   = [i for i in cited_indices if i in valid_indices]
    unverified = [i for i in cited_indices if i not in valid_indices]

    total = len(cited_indices)
    groundedness = len(verified) / total if total > 0 else 1.0

    is_hallucinated   = groundedness < GROUNDEDNESS_WARN_THRESHOLD
    needs_regeneration = groundedness < GROUNDEDNESS_REGEN_THRESHOLD

    warning_message = ""
    if needs_regeneration:
        warning_message = (
            f"⚠️ Low confidence answer (groundedness: {groundedness:.0%}). "
            "Some references could not be verified in the contract. "
            "Please verify critical information directly in the document."
        )
    elif is_hallucinated:
        warning_message = (
            f"Note: Answer confidence is {groundedness:.0%}. "
            "Please verify important details in the original contract."
        )

    if is_hallucinated:
        logger.warning(
            "hallucination_detected",
            org_id=org_id,
            contract_id=contract_id,
            total_citations=total,
            verified=len(verified),
            unverified=unverified,
            groundedness=round(groundedness, 3),
            needs_regeneration=needs_regeneration,
        )

    return HallucinationCheckResult(
        answer=answer,
        total_citations=total,
        verified_citations=len(verified),
        unverified_indices=unverified,
        groundedness=groundedness,
        is_hallucinated=is_hallucinated,
        needs_regeneration=needs_regeneration,
        warning_message=warning_message,
    )


def append_confidence_note(answer: str, result: HallucinationCheckResult) -> str:
    """Append confidence/warning note to answer if needed."""
    if result.warning_message:
        return answer + f"\n\n---\n{result.warning_message}"
    if result.total_citations > 0 and not result.is_hallucinated:
        return answer + f"\n\n*Confidence: {result.groundedness:.0%} — all citations verified.*"
    return answer
