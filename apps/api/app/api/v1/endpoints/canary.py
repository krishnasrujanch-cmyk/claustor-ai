"""
Claustor AI — Canary & Health endpoints
"""
from fastapi import APIRouter, Depends
from app.api.v1.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/v1/canary", tags=["canary"])


@router.post("/run")
async def trigger_canary(user=Depends(get_current_user)):
    """Manually trigger canary evaluation (super_admin only)."""
    if user.role != "super_admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="super_admin only")
    from app.infrastructure.security.canary import run_canary
    result = await run_canary()
    return {
        "accuracy":       round(result.accuracy * 100, 1),
        "passed":         result.passed,
        "total":          result.total_cases,
        "failed":         result.failed,
        "below_threshold":result.below_threshold,
        "status":         "DEGRADED" if result.below_threshold else "HEALTHY",
        "cases": [
            {
                "id":            r.case_id,
                "passed":        r.passed,
                "actual_type":   r.actual_type,
                "expected_type": r.expected_type,
                "actual_score":  r.actual_score,
                "expected_range":r.expected_range,
                "type_correct":  r.type_correct,
                "score_ok":      r.score_in_range,
                "level_ok":      r.level_correct,
                "error":         r.error,
            }
            for r in result.results
        ],
    }


@router.get("/status")
async def canary_status(user=Depends(get_current_user)):
    """Get last canary run result from Redis cache."""
    try:
        from app.infrastructure.database.redis import get_redis
        import json
        redis = await get_redis()
        cached = await redis.get("canary:last_result")
        if cached:
            return json.loads(cached)
        return {"status": "NO_RUN", "message": "Canary not yet run"}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}
