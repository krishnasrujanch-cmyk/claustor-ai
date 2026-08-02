"""
Structured Query Handler for Claustor AI Copilot.
Handles DB-based queries: expiry lists, counts, aggregations, missing clauses.
Returns formatted text context to inject into LLM prompt.
"""

from __future__ import annotations
import logging
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def run_structured_query(
    intent_sub_type: Optional[str],
    date_start: Optional[date],
    date_end: Optional[date],
    timeframe: Optional[str],
    query: str,
    org_id: UUID,
    db: AsyncSession,
    contract_id: Optional[UUID] = None,
) -> str:
    """
    Run the appropriate DB query based on intent sub-type.
    Returns formatted context string to inject into LLM prompt.
    """
    try:
        # Route to specific handler
        if sub_type_matches(intent_sub_type, ["expiry_list"]) or timeframe:
            return await _expiry_query(org_id, db, date_start, date_end, timeframe)
        
        if sub_type_matches(intent_sub_type, ["count_by_risk", "high_risk_list"]):
            return await _risk_query(org_id, db)
        
        if sub_type_matches(intent_sub_type, ["total_value"]):
            return await _value_query(org_id, db)
        
        if sub_type_matches(intent_sub_type, ["avg_risk"]):
            return await _avg_risk_query(org_id, db)
        
        if sub_type_matches(intent_sub_type, ["renewal_list", "auto_renewal"]):
            return await _renewal_query(org_id, db)
        
        if sub_type_matches(intent_sub_type, ["overdue_list"]) or timeframe == "overdue":
            return await _overdue_query(org_id, db)
        
        # Generic: fetch contract list with key metadata
        return await _contract_list_query(org_id, db, query)
    
    except Exception as e:
        logger.error("structured_query_failed", error=str(e), sub_type=intent_sub_type)
        return ""


def sub_type_matches(sub_type: Optional[str], patterns: list[str]) -> bool:
    if not sub_type:
        return False
    return any(p in sub_type for p in patterns)


async def _expiry_query(org_id, db, date_start, date_end, timeframe) -> str:
    today = date.today()
    if not date_start:
        date_start = today
    if not date_end:
        date_end = today + timedelta(days=30)

    r = await db.execute(text("""
        SELECT title, expiry_date, risk_level,
               COALESCE(contract_value::text, 'N/A') as value,
               auto_renewal, status
        FROM contracts
        WHERE org_id = :oid
          AND is_active = TRUE
          AND expiry_date BETWEEN :start AND :end
        ORDER BY expiry_date ASC
        LIMIT 20
    """), {"oid": str(org_id), "start": date_start, "end": date_end})
    rows = r.fetchall()

    label = {
        "next_month":    "next month",
        "this_month":    "this month",
        "this_week":     "this week",
        "next_week":     "next week",
        "next_30_days":  "the next 30 days",
        "next_90_days":  "the next 90 days",
        "overdue":       "that are overdue/expired",
        "this_year":     "this year",
    }.get(timeframe or "", f"between {date_start} and {date_end}")

    if not rows:
        return f"\n\nDATABASE RESULT: No contracts expiring {label}."

    lines = [f"\n\nDATABASE RESULT — Contracts expiring {label} ({len(rows)} found):\n"]
    for r in rows:
        auto = " [AUTO-RENEWAL]" if r[4] else ""
        lines.append(
            f"• {r[0]}: expires {r[1]}, risk={r[2]}, "
            f"value={r[3]}{auto}"
        )
    return "\n".join(lines)


async def _risk_query(org_id, db) -> str:
    r = await db.execute(text("""
        SELECT risk_level, COUNT(*) as cnt,
               ROUND(AVG(risk_score)::numeric, 1) as avg_score
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE AND status = 'analyzed'
        GROUP BY risk_level
        ORDER BY cnt DESC
    """), {"oid": str(org_id)})
    rows = r.fetchall()

    # Also get high risk list
    h = await db.execute(text("""
        SELECT title, risk_score, expiry_date
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE
          AND risk_level = 'high'
        ORDER BY risk_score DESC
        LIMIT 10
    """), {"oid": str(org_id)})
    high = h.fetchall()

    lines = ["\n\nDATABASE RESULT — Risk Distribution:\n"]
    for row in rows:
        lines.append(f"• {row[0].upper()}: {row[1]} contracts (avg score: {row[2]})")
    if high:
        lines.append(f"\nHigh Risk Contracts:")
        for h in high:
            exp = f", expires {h[2]}" if h[2] else ""
            lines.append(f"• {h[0]}: score {h[1]}{exp}")
    return "\n".join(lines)


async def _value_query(org_id, db) -> str:
    r = await db.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(contract_value) as with_value,
            SUM(contract_value) as total_value,
            AVG(contract_value) as avg_value,
            MAX(contract_value) as max_value
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE
    """), {"oid": str(org_id)})
    row = r.fetchone()
    if not row or not row[2]:
        return "\n\nDATABASE RESULT: No contract values recorded yet."

    top = await db.execute(text("""
        SELECT title, contract_value, currency
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE AND contract_value IS NOT NULL
        ORDER BY contract_value DESC LIMIT 5
    """), {"oid": str(org_id)})

    lines = [
        "\n\nDATABASE RESULT — Contract Values:",
        f"• Total portfolio value: {row[4]} ({row[1]} contracts with value)",
        f"• Average contract value: {round(row[3] or 0, 2)}",
        f"• Largest contract: {round(row[4] or 0, 2)}",
        "\nTop contracts by value:",
    ]
    for t in top.fetchall():
        lines.append(f"• {t[0]}: {t[1]} {t[2] or 'USD'}")
    return "\n".join(lines)


async def _avg_risk_query(org_id, db) -> str:
    r = await db.execute(text("""
        SELECT ROUND(AVG(risk_score)::numeric, 1) as avg,
               COUNT(*) as total,
               COUNT(CASE WHEN risk_level='high' THEN 1 END) as high,
               COUNT(CASE WHEN risk_level='medium' THEN 1 END) as medium,
               COUNT(CASE WHEN risk_level='low' THEN 1 END) as low
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE AND status = 'analyzed'
    """), {"oid": str(org_id)})
    row = r.fetchone()
    if not row:
        return "\n\nDATABASE RESULT: No analyzed contracts found."
    return (
        f"\n\nDATABASE RESULT — Risk Summary:\n"
        f"• Average risk score: {row[0]}/100\n"
        f"• Total analyzed: {row[1]}\n"
        f"• High risk: {row[2]} | Medium: {row[3]} | Low: {row[4]}"
    )


async def _renewal_query(org_id, db) -> str:
    r = await db.execute(text("""
        SELECT title, expiry_date, risk_level
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE AND auto_renewal = TRUE
        ORDER BY expiry_date ASC NULLS LAST
        LIMIT 15
    """), {"oid": str(org_id)})
    rows = r.fetchall()
    if not rows:
        return "\n\nDATABASE RESULT: No auto-renewal contracts found."
    lines = [f"\n\nDATABASE RESULT — Auto-renewal contracts ({len(rows)}):\n"]
    for r in rows:
        lines.append(f"• {r[0]}: expires {r[1] or 'N/A'}, risk={r[2]}")
    return "\n".join(lines)


async def _overdue_query(org_id, db) -> str:
    today = date.today()
    r = await db.execute(text("""
        SELECT title, expiry_date, risk_level,
               (CURRENT_DATE - expiry_date) as days_overdue
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE
          AND expiry_date < :today
        ORDER BY expiry_date ASC
        LIMIT 15
    """), {"oid": str(org_id), "today": today})
    rows = r.fetchall()
    if not rows:
        return "\n\nDATABASE RESULT: No overdue/expired contracts."
    lines = [f"\n\nDATABASE RESULT — Overdue contracts ({len(rows)}):\n"]
    for r in rows:
        lines.append(f"• {r[0]}: expired {r[1]} ({r[3]} days ago), risk={r[2]}")
    return "\n".join(lines)


async def _contract_list_query(org_id, db, query: str) -> str:
    """Generic contract list with metadata."""
    r = await db.execute(text("""
        SELECT title, status, risk_level, risk_score, expiry_date,
               COALESCE(contract_value::text, 'N/A') as value
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE
        ORDER BY created_at DESC
        LIMIT 10
    """), {"oid": str(org_id)})
    rows = r.fetchall()
    if not rows:
        return "\n\nDATABASE RESULT: No contracts found."
    lines = [f"\n\nDATABASE RESULT — Your contracts ({len(rows)} recent):\n"]
    for r in rows:
        exp = f", expires {r[4]}" if r[4] else ""
        lines.append(f"• {r[0]}: {r[1]}, risk={r[2]} ({r[3]}){exp}, value={r[5]}")
    return "\n".join(lines)


async def run_missing_clause_query(
    query: str,
    org_id: UUID,
    db: AsyncSession,
) -> str:
    """Find contracts missing a specific clause type."""
    import re
    # Extract clause type from query
    clause_keywords = {
        "nda": "confidentiality",
        "confidential": "confidentiality",
        "non.?compete": "non_compete",
        "terminat": "termination",
        "payment": "payment",
        "liabilit": "liability",
        "indemnif": "indemnification",
        "ip|intellectual property": "ip_ownership",
        "governing law": "governing_law",
        "arbitration|dispute": "dispute_resolution",
    }

    target_clause = None
    for pattern, clause_type in clause_keywords.items():
        if re.search(pattern, query.lower()):
            target_clause = clause_type
            break

    if not target_clause:
        return ""

    # Find contracts that have this clause type
    r = await db.execute(text("""
        SELECT DISTINCT c.title, c.id
        FROM contracts c
        JOIN clauses cl ON cl.contract_id = c.id
        WHERE c.org_id = :oid AND c.is_active = TRUE
          AND cl.clause_type = :ct
    """), {"oid": str(org_id), "ct": target_clause})
    has_clause = {row[0] for row in r.fetchall()}

    # Get all analyzed contracts
    r2 = await db.execute(text("""
        SELECT title FROM contracts
        WHERE org_id = :oid AND is_active = TRUE AND status = 'analyzed'
    """), {"oid": str(org_id)})
    all_contracts = {row[0] for row in r2.fetchall()}

    missing = all_contracts - has_clause

    lines = [
        f"\n\nDATABASE RESULT — Contracts WITHOUT {target_clause} clause:\n"
    ]
    if missing:
        for title in sorted(missing):
            lines.append(f"• {title}")
    else:
        lines.append(f"All contracts have a {target_clause} clause.")

    lines.append(f"\nContracts WITH {target_clause} clause: {len(has_clause)}")
    lines.append(f"Contracts WITHOUT {target_clause} clause: {len(missing)}")
    return "\n".join(lines)
