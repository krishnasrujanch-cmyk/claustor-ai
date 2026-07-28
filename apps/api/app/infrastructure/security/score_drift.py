"""
Claustor AI — Score Drift Detector
Detects when risk scores for the same clause change significantly
between pipeline runs (e.g. after model updates).

Drift signals:
  - Same clause text → score changes > DRIFT_THRESHOLD points
  - Used for: model degradation detection, consistency monitoring
"""
import structlog
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

DRIFT_THRESHOLD = 15        # alert if score drifts > 15 points
CRITICAL_THRESHOLD = 30     # critical alert if drift > 30 points


@dataclass
class DriftResult:
    clause_id: str
    previous_score: float
    current_score: float
    drift: float
    is_drift: bool
    is_critical: bool
    direction: str          # "up" | "down" | "stable"


def check_score_drift(
    clause_id: str,
    current_score: float,
    previous_score: float | None,
    org_id: str = "",
) -> DriftResult:
    """
    Compare current risk score against previous score for same clause.
    Called after pipeline scoring to detect model inconsistency.
    """
    if previous_score is None:
        return DriftResult(
            clause_id=clause_id,
            previous_score=0,
            current_score=current_score,
            drift=0,
            is_drift=False,
            is_critical=False,
            direction="stable",
        )

    drift = abs(current_score - previous_score)
    direction = (
        "up"   if current_score > previous_score + 2 else
        "down" if current_score < previous_score - 2 else
        "stable"
    )
    is_drift    = drift >= DRIFT_THRESHOLD
    is_critical = drift >= CRITICAL_THRESHOLD

    if is_critical:
        logger.error(
            "score_drift_critical",
            org_id=org_id,
            clause_id=clause_id,
            previous=previous_score,
            current=current_score,
            drift=drift,
            direction=direction,
        )
    elif is_drift:
        logger.warning(
            "score_drift_detected",
            org_id=org_id,
            clause_id=clause_id,
            previous=previous_score,
            current=current_score,
            drift=drift,
            direction=direction,
        )

    return DriftResult(
        clause_id=clause_id,
        previous_score=previous_score,
        current_score=current_score,
        drift=drift,
        is_drift=is_drift,
        is_critical=is_critical,
        direction=direction,
    )


async def check_contract_drift(
    contract_id: str,
    clauses: list[dict],
    db,
    org_id: str = "",
) -> list[DriftResult]:
    """
    Check score drift for all clauses in a contract by comparing
    against previously stored scores in DB.
    Returns list of drift results (only clauses with drift).
    """
    try:
        from sqlalchemy import text
        results = []
        for clause in clauses:
            clause_type = clause.get("clause_type", "")
            current_score = float(clause.get("risk_score", 0))

            # Fetch previous score for same contract + clause_type
            row = await db.execute(text("""
                SELECT risk_score FROM clauses
                WHERE contract_id = :cid
                  AND clause_type = :ct
                ORDER BY created_at DESC
                LIMIT 1
            """), {"cid": contract_id, "ct": clause_type})
            prev = row.fetchone()
            prev_score = float(prev[0]) if prev else None

            drift = check_score_drift(
                clause_id=f"{contract_id}:{clause_type}",
                current_score=current_score,
                previous_score=prev_score,
                org_id=org_id,
            )
            if drift.is_drift:
                results.append(drift)

        return results

    except Exception as e:
        logger.warning("drift_check_failed", error=str(e))
        return []
