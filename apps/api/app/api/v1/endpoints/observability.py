"""
Claustor AI — Observability API
Exposes AI metrics for the admin dashboard.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/summary")
async def get_summary(
    days: int = Query(30, ge=1, le=90),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI usage summary for the org — last N days."""
    DKU_ORG_ID = "00000000-0000-0000-0000-000000000002"
    is_dku = str(user.org_id) == DKU_ORG_ID
    org_filter = "" if is_dku else "AND org_id = :org_id"

    r = await db.execute(text(f"""
        SELECT
            COUNT(*)                                        AS total_calls,
            COALESCE(SUM(total_tokens), 0)                 AS total_tokens,
            COALESCE(SUM(cost_usd), 0)                     AS total_cost_usd,
            COALESCE(AVG(latency_ms), 0)                   AS avg_latency_ms,
            COALESCE(PERCENTILE_CONT(0.5)
                WITHIN GROUP (ORDER BY latency_ms), 0)     AS p50_latency_ms,
            COALESCE(PERCENTILE_CONT(0.95)
                WITHIN GROUP (ORDER BY latency_ms), 0)     AS p95_latency_ms,
            COALESCE(AVG(groundedness) FILTER
                (WHERE groundedness IS NOT NULL), 1)        AS avg_groundedness,
            COUNT(*) FILTER (WHERE hallucination = TRUE)   AS hallucination_count,
            COUNT(*) FILTER (WHERE judge_triggered = TRUE) AS judge_calls,
            COUNT(*) FILTER (WHERE injection_detected = TRUE) AS injections_detected,
            COUNT(*) FILTER (WHERE safety_passed = FALSE)  AS safety_blocks,
            COUNT(*) FILTER (WHERE cache_hit = TRUE)       AS cache_hits
        FROM ai_observability
        WHERE created_at > NOW() - INTERVAL '{days} days'
        {org_filter}
    """), {"org_id": str(user.org_id)} if not is_dku else {})

    row = r.fetchone()
    if not row:
        return {"total_calls": 0}

    total_calls = row[0] or 0
    cache_hits  = row[11] or 0
    hall_count  = row[7] or 0

    return {
        "period_days":          days,
        "total_calls":          total_calls,
        "total_tokens":         int(row[1] or 0),
        "total_cost_usd":       round(float(row[2] or 0), 4),
        "avg_latency_ms":       round(float(row[3] or 0)),
        "p50_latency_ms":       round(float(row[4] or 0)),
        "p95_latency_ms":       round(float(row[5] or 0)),
        "avg_groundedness":     round(float(row[6] or 1), 3),
        "hallucination_rate":   round(hall_count / total_calls, 4) if total_calls else 0,
        "hallucination_count":  hall_count,
        "judge_calls":          int(row[8] or 0),
        "injections_detected":  int(row[9] or 0),
        "safety_blocks":        int(row[10] or 0),
        "cache_hit_rate":       round(cache_hits / total_calls, 3) if total_calls else 0,
        "cache_hits":           cache_hits,
    }


@router.get("/by-role")
async def get_by_role(
    days: int = Query(30, ge=1, le=90),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cost and usage broken down by agent role."""
    DKU_ORG_ID = "00000000-0000-0000-0000-000000000002"
    is_dku = str(user.org_id) == DKU_ORG_ID
    org_filter = "" if is_dku else "AND org_id = :org_id"

    r = await db.execute(text(f"""
        SELECT
            agent_role,
            COUNT(*)                    AS calls,
            SUM(total_tokens)           AS tokens,
            ROUND(SUM(cost_usd)::numeric, 6) AS cost_usd,
            ROUND(AVG(latency_ms))      AS avg_latency_ms
        FROM ai_observability
        WHERE created_at > NOW() - INTERVAL '{days} days'
        {org_filter}
        GROUP BY agent_role
        ORDER BY cost_usd DESC
    """), {"org_id": str(user.org_id)} if not is_dku else {})

    return {"roles": [
        {"role": row[0], "calls": row[1], "tokens": row[2],
         "cost_usd": float(row[3] or 0), "avg_latency_ms": int(row[4] or 0)}
        for row in r.fetchall()
    ]}


@router.get("/by-org")
async def get_by_org(
    days: int = Query(30, ge=1, le=90),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cost per org — super_admin only."""
    if user.role != "super_admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="super_admin only")

    r = await db.execute(text(f"""
        SELECT
            o.name                      AS org_name,
            o.plan,
            COUNT(obs.id)               AS calls,
            COALESCE(SUM(obs.total_tokens), 0)  AS tokens,
            COALESCE(ROUND(SUM(obs.cost_usd)::numeric, 4), 0) AS cost_usd
        FROM ai_observability obs
        LEFT JOIN organisations o ON o.id = obs.org_id
        WHERE obs.created_at > NOW() - INTERVAL '{days} days'
        GROUP BY o.name, o.plan
        ORDER BY cost_usd DESC
        LIMIT 50
    """))

    return {"orgs": [
        {"name": row[0], "plan": row[1], "calls": row[2],
         "tokens": row[3], "cost_usd": float(row[4] or 0)}
        for row in r.fetchall()
    ]}


@router.get("/latency-trend")
async def get_latency_trend(
    days: int = Query(7, ge=1, le=30),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Daily P50/P95 latency trend."""
    DKU_ORG_ID = "00000000-0000-0000-0000-000000000002"
    is_dku = str(user.org_id) == DKU_ORG_ID
    org_filter = "" if is_dku else "AND org_id = :org_id"

    r = await db.execute(text(f"""
        SELECT
            DATE(created_at)            AS day,
            ROUND(PERCENTILE_CONT(0.5)
                WITHIN GROUP (ORDER BY latency_ms))  AS p50,
            ROUND(PERCENTILE_CONT(0.95)
                WITHIN GROUP (ORDER BY latency_ms))  AS p95,
            COUNT(*)                    AS calls,
            ROUND(SUM(cost_usd)::numeric, 4) AS cost_usd
        FROM ai_observability
        WHERE created_at > NOW() - INTERVAL '{days} days'
        {org_filter}
        GROUP BY DATE(created_at)
        ORDER BY day DESC
    """), {"org_id": str(user.org_id)} if not is_dku else {})

    return {"trend": [
        {"day": str(row[0]), "p50_ms": int(row[1] or 0),
         "p95_ms": int(row[2] or 0), "calls": row[3],
         "cost_usd": float(row[4] or 0)}
        for row in r.fetchall()
    ]}


@router.get("/feedback")
async def get_feedback_stats(
    days: int = Query(30, ge=1, le=90),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User feedback (thumbs up/down) stats."""
    DKU_ORG_ID = "00000000-0000-0000-0000-000000000002"
    is_dku = str(user.org_id) == DKU_ORG_ID
    org_filter = "" if is_dku else "AND org_id = :org_id"

    r = await db.execute(text(f"""
        SELECT
            user_feedback,
            COUNT(*) AS count
        FROM ai_observability
        WHERE created_at > NOW() - INTERVAL '{days} days'
          AND user_feedback IS NOT NULL
          {org_filter}
        GROUP BY user_feedback
    """), {"org_id": str(user.org_id)} if not is_dku else {})

    rows = r.fetchall()
    total = sum(row[1] for row in rows)
    return {
        "total_rated": total,
        "breakdown": {row[0]: row[1] for row in rows},
        "satisfaction_rate": round(
            next((r[1] for r in rows if r[0]=="thumbs_up"), 0) / total, 3
        ) if total else 0,
    }
