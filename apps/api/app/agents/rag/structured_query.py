"""
Structured Query Handler v2 — Claustor AI Copilot
Covers all 8 industries with full filter support.
"""

from __future__ import annotations
import structlog
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = structlog.get_logger(__name__)


async def _single_contract_facts(org_id, db, contract_id) -> str:
    """Fetch all key facts for a single contract — used when contract_id is scoped."""
    r = await db.execute(text("""
        SELECT title, expiry_date, effective_date, contract_value, contract_currency,
               risk_level, risk_score, counterparty, contract_type, governing_law,
               auto_renewal, renewal_notice_days, status
        FROM contracts
        WHERE org_id = :oid AND id = :cid AND is_active = TRUE
    """), {"oid": str(org_id), "cid": str(contract_id)})
    row = r.fetchone()
    if not row:
        return ""
    val = _fmt_amount(float(row[3]), row[4]) if row[3] else "Not specified"
    renew = f"Yes (notice: {row[11]} days)" if row[10] else "No"
    return (
        f"\n\n📊 Contract Facts:\n"
        f"• Title: {row[0]}\n"
        f"• Type: {row[8] or 'N/A'}\n"
        f"• Counterparty: {row[7] or 'N/A'}\n"
        f"• Value: {val}\n"
        f"• Effective: {row[2] or 'N/A'}\n"
        f"• Expiry: {row[1] or 'Not specified'}\n"
        f"• Risk: {row[5]} ({row[6]})\n"
        f"• Governing Law: {row[9] or 'N/A'}\n"
        f"• Auto-renewal: {renew}\n"
        f"• Status: {row[12]}"
    )



async def _party_identifier_query(
    org_id, db, filters: dict, query: str, contract_id=None
) -> str:
    """
    Query party_identifiers JSONB directly from contracts table.
    Returns party names, roles, and all registration identifiers.
    """
    from sqlalchemy import text
    import json

    where = "org_id = :org_id"
    params: dict = {"org_id": str(org_id)}
    if contract_id:
        where += " AND id = :contract_id"
        params["contract_id"] = str(contract_id)

    rows = await db.execute(text(f"""
        SELECT title, counterparty, party_identifiers
        FROM contracts
        WHERE {where}
          AND party_identifiers IS NOT NULL
          AND party_identifiers != '[]'::jsonb
        ORDER BY updated_at DESC
        LIMIT 5
    """), params)

    results = rows.fetchall()
    if not results:
        return ""

    lines = []
    for row in results:
        title = row[0] or "Contract"
        parties = row[2] or []
        if not parties:
            continue
        lines.append(f"Contract: {title}")
        for party in parties:
            name = party.get("party_name", "")
            role = party.get("role", "Party")
            addr = party.get("address", "")
            ids  = party.get("identifiers", [])
            lines.append(f"  {name} ({role}):")
            if addr:
                lines.append(f"    Address: {addr}")
            for id_info in ids:
                lines.append(f"    {id_info.get('type','')}: {id_info.get('value','')}")
        lines.append("")

    return "\n".join(lines)


async def run_structured_query(
    intent_sub_type: Optional[str],
    date_start:      Optional[date],
    date_end:        Optional[date],
    timeframe:       Optional[str],
    query:           str,
    org_id:          UUID,
    db:              AsyncSession,
    contract_id:     Optional[UUID] = None,
    filters:         dict = None,
) -> str:
    filters = filters or {}
    try:
        # When scoped to a single contract with no timeframe — use contract facts
        if contract_id and not date_start and not date_end:
            q_lower = query.lower()
            # Only use facts for specific factual questions
            fact_keywords = ["expir","when","value","worth","risk","counterparty",
                           "party","govern","law","renewal","effective","status",
                           "type","currency","notice"]
            if any(k in q_lower for k in fact_keywords):
                return await _single_contract_facts(org_id, db, contract_id)
        # Route by sub-type or timeframe
        if timeframe or _matches(intent_sub_type, ["expiry", "due", "matur", "renew", "overdue"]):
            return await _expiry_query(org_id, db, date_start, date_end, timeframe, filters, contract_id=contract_id)

        if _matches(intent_sub_type, ["high_risk", "count_by_risk"]):
            return await _risk_query(org_id, db, filters, contract_id=contract_id)

        if _matches(intent_sub_type, ["top_by_value", "high_value", "total_value"]):
            return await _value_query(org_id, db, filters, contract_id=contract_id)

        if _matches(intent_sub_type, ["avg_risk"]):
            return await _avg_risk_query(org_id, db)

        if _matches(intent_sub_type, ["renewal_list"]):
            return await _renewal_query(org_id, db, filters, contract_id=contract_id)

        if _matches(intent_sub_type, ["overdue_list"]):
            return await _overdue_query(org_id, db)

        if _matches(intent_sub_type, ["by_type"]):
            return await _type_query(org_id, db, filters, contract_id=contract_id)

        if _matches(intent_sub_type, ["by_counterparty"]):
            return await _counterparty_query(org_id, db, filters, query, contract_id=contract_id)
        if _matches(intent_sub_type, ["party_identifier", "gstin", "cin", "pan", "vat",
                                       "registration", "tax_id", "company_number"]):
            return await _party_identifier_query(org_id, db, filters, query, contract_id=contract_id)

        if _matches(intent_sub_type, ["by_status", "pending_review"]):
            return await _status_query(org_id, db, filters, contract_id=contract_id)

        if _matches(intent_sub_type, ["value_filter"]):
            return await _value_filter_query(org_id, db, filters, contract_id=contract_id)

        if _matches(intent_sub_type, ["milestone_list"]):
            return await _milestone_query(org_id, db)

        if _matches(intent_sub_type, ["count_total"]):
            return await _count_total_query(org_id, db)

        # Generic contract list with all filters
        return await _smart_contract_list(org_id, db, filters, query, contract_id=contract_id)

    except Exception as e:
        logger.error(f"structured_query_failed: {e}")
        return ""


def _matches(sub_type: Optional[str], keywords: list) -> bool:
    if not sub_type: return False
    return any(k in sub_type for k in keywords)


def _timeframe_label(timeframe: Optional[str], date_start, date_end) -> str:
    labels = {
        "next_month": "next month", "this_month": "this month",
        "next_week": "next week", "this_week": "this week",
        "next_year": "next year", "this_year": "this year",
        "soon": "the next 90 days", "overdue": "that are overdue",
    }
    if timeframe in labels:
        return labels[timeframe]
    if timeframe and timeframe.startswith("FY"):
        return f"in {timeframe}"
    if timeframe and timeframe.startswith("Q"):
        return f"in {timeframe}"
    if timeframe and "years" in timeframe:
        n = timeframe.split("_")[1]
        return f"in the next {n} years"
    if timeframe and "months" in timeframe:
        n = timeframe.split("_")[1]
        return f"in the next {n} months"
    if date_start and date_end:
        return f"between {date_start} and {date_end}"
    return ""


async def _expiry_query(org_id, db, date_start, date_end, timeframe, filters, contract_id=None) -> str:
    today = date.today()
    if not date_start: date_start = today
    if not date_end:   date_end = today + timedelta(days=90)

    where = ["org_id = :oid", "is_active = TRUE", "expiry_date BETWEEN :start AND :end"]
    params = {"oid": str(org_id), "start": date_start, "end": date_end}
    if contract_id:
        where.append("id = :cid")
        params["cid"] = str(contract_id)

    if filters.get("risk_level"):
        where.append("risk_level = :rl")
        params["rl"] = filters["risk_level"]
    if filters.get("contract_type"):
        where.append("contract_type ILIKE :ct")
        params["ct"] = f"%{filters['contract_type']}%"

    order = "expiry_date ASC"
    limit = filters.get("top_n", 20)

    r = await db.execute(text(f"""
        SELECT title, expiry_date, risk_level, risk_score,
               COALESCE(contract_value::text,'N/A') as val,
               contract_currency, auto_renewal, counterparty, contract_type
        FROM contracts
        WHERE {' AND '.join(where)}
        ORDER BY {order}
        LIMIT {limit}
    """), params)
    rows = r.fetchall()

    label = _timeframe_label(timeframe, date_start, date_end)

    if not rows:
        r2 = await db.execute(text("""
            SELECT title, risk_level FROM contracts
            WHERE org_id = :oid AND is_active = TRUE
              AND expiry_date IS NULL AND status = 'analyzed'
            ORDER BY title LIMIT 10
        """), {"oid": str(org_id)})
        no_date = r2.fetchall()
        msg = f"\n\n�� No contracts found expiring {label}."
        if no_date:
            msg += f"\n\nNote: {len(no_date)} contracts have no expiry date recorded:"
            for nd in no_date:
                msg += f"\n• {nd[0]} (risk={nd[1]})"
        return msg

    lines = [f"\n\n📊 Contracts expiring {label} ({len(rows)} found):\n"]
    for row in rows:
        val = f"{row[4]} {row[5] or ''}" if row[4] != 'N/A' else "Value not set"
        renew = " [AUTO-RENEWAL]" if row[7] else ""
        party = f", counterparty: {row[7]}" if row[7] else ""
        lines.append(
            f"• {row[0]}: expires {row[1]}, risk={row[2]} ({row[3]}), "
            f"value={val}{party}{renew}"
        )
    return "\n".join(lines)


async def _risk_query(org_id, db, filters, contract_id=None) -> str:
    risk_where = ["org_id = :oid", "is_active = TRUE", "status = 'analyzed'"]
    params = {"oid": str(org_id)}

    if filters.get("min_risk_score"):
        risk_where.append("risk_score >= :mrs")
        params["mrs"] = filters["min_risk_score"]

    r = await db.execute(text(f"""
        SELECT risk_level, COUNT(*) as cnt,
               ROUND(AVG(risk_score)::numeric,1) as avg_score
        FROM contracts WHERE {' AND '.join(risk_where)}
        GROUP BY risk_level ORDER BY cnt DESC
    """), params)
    dist = r.fetchall()

    rl_filter = filters.get("risk_level", "high")
    h = await db.execute(text("""
        SELECT title, risk_score, expiry_date, counterparty,
               COALESCE(contract_value::text,'N/A') as val
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE AND risk_level = :rl
        ORDER BY risk_score DESC LIMIT 10
    """), {"oid": str(org_id), "rl": rl_filter})
    high = h.fetchall()

    lines = ["\n\n📊 Risk Distribution:\n"]
    for row in dist:
        lines.append(f"• {row[0].upper()}: {row[1]} contracts (avg score: {row[2]})")
    if high:
        lines.append(f"\n{rl_filter.title()} Risk Contracts:")
        for h in high:
            exp = f", expires {h[2]}" if h[2] else ""
            party = f", party: {h[3]}" if h[3] else ""
            lines.append(f"• {h[0]}: score {h[1]}, value={h[4]}{exp}{party}")
    return "\n".join(lines)


async def _value_query(org_id, db, filters, contract_id=None) -> str:
    where = ["org_id = :oid", "is_active = TRUE", "contract_value IS NOT NULL"]
    params = {"oid": str(org_id)}

    if filters.get("min_value"):
        where.append("contract_value >= :mv")
        params["mv"] = filters["min_value"]
    if filters.get("max_value"):
        where.append("contract_value <= :xv")
        params["xv"] = filters["max_value"]

    limit = filters.get("top_n", 10)

    r = await db.execute(text(f"""
        SELECT title, contract_value, COALESCE(contract_currency,'USD') as currency,
               risk_level, expiry_date, counterparty
        FROM contracts
        WHERE {' AND '.join(where)}
        ORDER BY contract_value DESC
        LIMIT {limit}
    """), params)
    rows = r.fetchall()

    # Totals
    t = await db.execute(text("""
        SELECT COUNT(*) as total, SUM(contract_value) as total_val,
               AVG(contract_value) as avg_val
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE AND contract_value IS NOT NULL
    """), {"oid": str(org_id)})
    totals = t.fetchone()

    lines = [f"\n\n📊 Contract Values:\n"]
    lines.append(f"• Total portfolio: {_fmt_amount(totals[1])} ({totals[0]} contracts)")
    lines.append(f"• Average value: {_fmt_amount(totals[2])}\n")

    if rows:
        lines.append(f"Top {limit} by value:")
        for i, r in enumerate(rows, 1):
            exp = f", expires {r[4]}" if r[4] else ""
            party = f", {r[5]}" if r[5] else ""
            lines.append(f"{i}. {r[0]}: {_fmt_amount(r[1], r[2] or 'USD')}, "
                        f"risk={r[3]}{party}{exp}")
    return "\n".join(lines)


async def _avg_risk_query(org_id, db, contract_id=None) -> str:
    r = await db.execute(text("""
        SELECT ROUND(AVG(risk_score)::numeric,1),
               COUNT(*),
               COUNT(CASE WHEN risk_level='high'   THEN 1 END),
               COUNT(CASE WHEN risk_level='medium' THEN 1 END),
               COUNT(CASE WHEN risk_level='low'    THEN 1 END),
               MAX(risk_score), MIN(risk_score)
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE AND status = 'analyzed'
    """), {"oid": str(org_id)})
    row = r.fetchone()
    if not row: return "\n\n�� No analyzed contracts."
    return (
        f"\n\n📊 Risk Summary:\n"
        f"• Average risk score: {row[0]}/100\n"
        f"• Total analyzed: {row[1]}\n"
        f"• High risk: {row[2]} | Medium: {row[3]} | Low: {row[4]}\n"
        f"• Highest score: {row[5]} | Lowest: {row[6]}"
    )


async def _renewal_query(org_id, db, filters, contract_id=None) -> str:
    r = await db.execute(text("""
        SELECT title, expiry_date, risk_level, counterparty,
               renewal_notice_days
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE AND auto_renewal = TRUE
        ORDER BY expiry_date ASC NULLS LAST LIMIT 20
    """), {"oid": str(org_id)})
    rows = r.fetchall()
    if not rows:
        return "\n\n�� No auto-renewal contracts found."
    lines = [f"\n\n📊 Auto-renewal contracts ({len(rows)}):\n"]
    for r in rows:
        notice = f", notice: {r[4]} days" if r[4] else ""
        party = f", party: {r[3]}" if r[3] else ""
        lines.append(f"• {r[0]}: expires {r[1] or 'N/A'}, risk={r[2]}{party}{notice}")
    return "\n".join(lines)


async def _overdue_query(org_id, db, contract_id=None) -> str:
    today = date.today()
    r = await db.execute(text("""
        SELECT title, expiry_date, risk_level, counterparty,
               (CURRENT_DATE - expiry_date) as days_overdue
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE AND expiry_date < :today
        ORDER BY expiry_date ASC LIMIT 20
    """), {"oid": str(org_id), "today": today})
    rows = r.fetchall()
    if not rows: return "\n\n�� No overdue contracts."
    lines = [f"\n\n📊 Overdue contracts ({len(rows)}):\n"]
    for r in rows:
        lines.append(f"• {r[0]}: expired {r[1]} ({r[4]} days ago), risk={r[2]}")
    return "\n".join(lines)


async def _type_query(org_id, db, filters, contract_id=None) -> str:
    ct = filters.get("contract_type", "")
    where = ["org_id = :oid", "is_active = TRUE"]
    params = {"oid": str(org_id)}
    if ct:
        where.append("contract_type ILIKE :ct")
        params["ct"] = f"%{ct}%"

    r = await db.execute(text(f"""
        SELECT contract_type, COUNT(*) as cnt,
               ROUND(AVG(risk_score)::numeric,1) as avg_risk
        FROM contracts WHERE {' AND '.join(where)}
        GROUP BY contract_type ORDER BY cnt DESC
    """), params)
    rows = r.fetchall()

    if ct:
        # Show specific type list
        r2 = await db.execute(text("""
            SELECT title, risk_level, expiry_date, counterparty
            FROM contracts
            WHERE org_id = :oid AND is_active = TRUE
              AND contract_type ILIKE :ct
            ORDER BY risk_score DESC LIMIT 15
        """), {"oid": str(org_id), "ct": f"%{ct}%"})
        contracts = r2.fetchall()
        lines = [f"\n\n📊 {ct} contracts ({len(contracts)} found):\n"]
        for c in contracts:
            exp = f", expires {c[2]}" if c[2] else ""
            party = f", {c[3]}" if c[3] else ""
            lines.append(f"• {c[0]}: risk={c[1]}{party}{exp}")
        return "\n".join(lines)

    lines = ["\n\n📊 Contracts by Type:\n"]
    for row in rows:
        ct_label = row[0] or "Unclassified"
        lines.append(f"• {ct_label}: {row[1]} contracts (avg risk: {row[2]})")
    return "\n".join(lines)


async def _counterparty_query(org_id, db, filters, query, contract_id=None) -> str:
    party = filters.get("counterparty", "")
    if not party:
        # Extract from query
        import re
        m = re.search(r'(?:with|from|by|for)\s+([A-Z][^,.\n]{2,40})', query, re.IGNORECASE)
        if m: party = m.group(1).strip()

    if not party:
        # Show all counterparties
        r = await db.execute(text("""
            SELECT counterparty, COUNT(*) as cnt,
                   SUM(contract_value) as total_val
            FROM contracts
            WHERE org_id = :oid AND is_active = TRUE
              AND counterparty IS NOT NULL
            GROUP BY counterparty ORDER BY cnt DESC LIMIT 15
        """), {"oid": str(org_id)})
        rows = r.fetchall()
        lines = ["\n\n📊 Contracts by Counterparty:\n"]
        for row in rows:
            val = f", value: {_fmt_amount(row[2])}" if row[2] else ""
            lines.append(f"• {row[0]}: {row[1]} contract(s){val}")
        return "\n".join(lines)

    r = await db.execute(text("""
        SELECT title, risk_level, expiry_date, contract_value,
               contract_currency, status
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE
          AND counterparty ILIKE :party
        ORDER BY risk_score DESC LIMIT 10
    """), {"oid": str(org_id), "party": f"%{party}%"})
    rows = r.fetchall()

    if not rows:
        return f"\n\n�� No contracts found with counterparty matching '{party}'."

    lines = [f"\n\n📊 Contracts with {party} ({len(rows)} found):\n"]
    for r in rows:
        exp = f", expires {r[2]}" if r[2] else ""
        val = f", value: {_fmt_amount(r[3], r[4])}" if r[3] else ""
        lines.append(f"• {r[0]}: risk={r[1]}, status={r[5]}{val}{exp}")
    return "\n".join(lines)


async def _status_query(org_id, db, filters, contract_id=None) -> str:
    where = ["org_id = :oid", "is_active = TRUE"]
    params = {"oid": str(org_id)}

    if filters.get("flagged"):
        where.append("flagged_for_review = TRUE")
    elif filters.get("review_status"):
        where.append("review_status = :rs")
        params["rs"] = filters["review_status"]
    else:
        where.append("(review_status = 'pending' OR flagged_for_review = TRUE)")

    r = await db.execute(text(f"""
        SELECT title, review_status, risk_level, flagged_for_review,
               counterparty, expiry_date
        FROM contracts WHERE {' AND '.join(where)}
        ORDER BY created_at DESC LIMIT 15
    """), params)
    rows = r.fetchall()

    status_label = filters.get("review_status", "pending review")
    if not rows:
        return f"\n\n�� No contracts with status '{status_label}'."

    lines = [f"\n\n📊 Contracts ({status_label}) — {len(rows)} found:\n"]
    for r in rows:
        flagged = " [FLAGGED]" if r[3] else ""
        party = f", {r[4]}" if r[4] else ""
        exp = f", expires {r[5]}" if r[5] else ""
        lines.append(f"• {r[0]}: {r[1] or 'no review'}, risk={r[2]}{party}{flagged}{exp}")
    return "\n".join(lines)


async def _value_filter_query(org_id, db, filters, contract_id=None) -> str:
    where = ["org_id = :oid", "is_active = TRUE", "contract_value IS NOT NULL"]
    params = {"oid": str(org_id)}

    if filters.get("min_value"):
        where.append("contract_value >= :mv")
        params["mv"] = filters["min_value"]
    if filters.get("max_value"):
        where.append("contract_value <= :xv")
        params["xv"] = filters["max_value"]
    if filters.get("risk_level"):
        where.append("risk_level = :rl")
        params["rl"] = filters["risk_level"]

    limit = filters.get("top_n", 15)
    r = await db.execute(text(f"""
        SELECT title, contract_value, contract_currency, risk_level,
               expiry_date, counterparty
        FROM contracts WHERE {' AND '.join(where)}
        ORDER BY contract_value DESC LIMIT {limit}
    """), params)
    rows = r.fetchall()

    min_v = filters.get("min_value")
    max_v = filters.get("max_value")
    label = ""
    if min_v: label += f"above {_fmt_amount(min_v)} "
    if max_v: label += f"below {_fmt_amount(max_v)}"

    if not rows:
        return f"\n\n�� No contracts found {label.strip()}."

    lines = [f"\n\n📊 Contracts {label.strip()} ({len(rows)} found):\n"]
    for r in rows:
        exp = f", expires {r[4]}" if r[4] else ""
        party = f", {r[5]}" if r[5] else ""
        lines.append(f"• {r[0]}: {_fmt_amount(r[1], r[2] or 'USD')}, risk={r[3]}{party}{exp}")
    return "\n".join(lines)


async def _milestone_query(org_id, db, contract_id=None) -> str:
    r = await db.execute(text("""
        SELECT c.title, o.title as ob_title, o.due_date, o.obligation_type,
               o.description
        FROM obligations o
        JOIN contracts c ON c.id = o.contract_id
        WHERE c.org_id = :oid AND c.is_active = TRUE
          AND o.due_date >= CURRENT_DATE
          AND o.obligation_type IN ('payment','compliance','regulatory','certification','delivery')
        ORDER BY o.due_date ASC LIMIT 20
    """), {"oid": str(org_id)})
    rows = r.fetchall()

    if not rows:
        return "\n\n�� No upcoming milestones/compliance deadlines found."

    lines = [f"\n\n📊 Upcoming milestones & deadlines ({len(rows)}):\n"]
    for r in rows:
        lines.append(f"• [{r[3].upper()}] {r[1]} — {r[0]}: due {r[2]}")
        if r[4]: lines.append(f"  {r[4][:100]}")
    return "\n".join(lines)


async def _count_total_query(org_id, db, contract_id=None) -> str:
    r = await db.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN status='analyzed' THEN 1 END) as analyzed,
            COUNT(CASE WHEN status='queued' THEN 1 END) as queued,
            COUNT(CASE WHEN status='failed' THEN 1 END) as failed,
            COUNT(CASE WHEN risk_level='high' THEN 1 END) as high_risk,
            COUNT(CASE WHEN expiry_date < CURRENT_DATE THEN 1 END) as expired,
            COUNT(CASE WHEN auto_renewal=TRUE THEN 1 END) as auto_renew
        FROM contracts
        WHERE org_id = :oid AND is_active = TRUE
    """), {"oid": str(org_id)})
    row = r.fetchone()
    if not row: return "\n\n�� No contracts found."
    return (
        f"\n\n📊 Contract Summary:\n"
        f"• Total contracts: {row[0]}\n"
        f"• Analyzed: {row[1]} | Queued: {row[2]} | Failed: {row[3]}\n"
        f"• High risk: {row[4]}\n"
        f"• Expired/overdue: {row[5]}\n"
        f"• Auto-renewal: {row[6]}"
    )


async def _smart_contract_list(org_id, db, filters, query, contract_id=None) -> str:
    """Fallback: smart contract list with any applicable filters."""
    where = ["org_id = :oid", "is_active = TRUE"]
    params = {"oid": str(org_id)}
    if contract_id:
        where.append("id = :cid")
        params["cid"] = str(contract_id)

    if filters.get("risk_level"):
        where.append("risk_level = :rl"); params["rl"] = filters["risk_level"]
    if filters.get("contract_type"):
        where.append("contract_type ILIKE :ct"); params["ct"] = f"%{filters['contract_type']}%"
    if filters.get("min_value"):
        where.append("contract_value >= :mv"); params["mv"] = filters["min_value"]
    if filters.get("governing_law"):
        where.append("governing_law ILIKE :gl"); params["gl"] = f"%{filters['governing_law']}%"
    if filters.get("auto_renewal"):
        where.append("auto_renewal = TRUE")
    if filters.get("counterparty"):
        where.append("counterparty ILIKE :cp"); params["cp"] = f"%{filters['counterparty']}%"

    order = "risk_score DESC"
    limit = filters.get("top_n", 10)

    r = await db.execute(text(f"""
        SELECT title, risk_level, risk_score, expiry_date,
               COALESCE(contract_value::text,'N/A') as val,
               counterparty, contract_type
        FROM contracts WHERE {' AND '.join(where)}
        ORDER BY {order} LIMIT {limit}
    """), params)
    rows = r.fetchall()

    if not rows: return "\n\n�� No contracts found matching your criteria."
    lines = [f"\n\n📊 Contracts ({len(rows)} found):\n"]
    for r in rows:
        exp = f", expires {r[3]}" if r[3] else ""
        party = f", {r[5]}" if r[5] else ""
        lines.append(f"• {r[0]}: risk={r[1]} ({r[2]}), type={r[6] or 'N/A'}, value={r[4]}{party}{exp}")
    return "\n".join(lines)


async def run_missing_clause_query(query: str, org_id: UUID, db: AsyncSession) -> str:
    import re
    clause_keywords = {
        r"nda|confidential":             "confidentiality",
        r"non.?compete":                 "non_compete",
        r"terminat":                     "termination",
        r"payment":                      "payment",
        r"liabilit":                     "liability",
        r"indemnif":                     "indemnification",
        r"ip|intellectual property":     "ip_ownership",
        r"governing law|jurisdiction":   "governing_law",
        r"arbitration|dispute":          "dispute_resolution",
        r"force majeure":                "force_majeure",
        r"audit":                        "audit_rights",
        r"warranty|warrantee":           "warranty",
        r"insurance":                    "insurance",
        r"data protection|gdpr|hipaa":   "data_protection",
    }
    target_clause = None
    for pattern, clause_type in clause_keywords.items():
        if re.search(pattern, query.lower()):
            target_clause = clause_type
            break

    if not target_clause:
        return ""

    r = await db.execute(text("""
        SELECT DISTINCT c.title
        FROM contracts c JOIN clauses cl ON cl.contract_id = c.id
        WHERE c.org_id = :oid AND c.is_active = TRUE AND cl.clause_type = :ct
    """), {"oid": str(org_id), "ct": target_clause})
    has_clause = {row[0] for row in r.fetchall()}

    r2 = await db.execute(text("""
        SELECT title FROM contracts
        WHERE org_id = :oid AND is_active = TRUE AND status = 'analyzed'
    """), {"oid": str(org_id)})
    all_contracts = {row[0] for row in r2.fetchall()}
    missing = all_contracts - has_clause

    lines = [f"\n\n📊 {target_clause.replace('_',' ').title()} clause analysis:\n"]
    lines.append(f"• Contracts WITH clause: {len(has_clause)}")
    lines.append(f"• Contracts WITHOUT clause: {len(missing)}\n")
    if missing:
        lines.append("Contracts missing this clause:")
        for title in sorted(missing):
            lines.append(f"  ✗ {title}")
    if has_clause:
        lines.append("\nContracts that have this clause:")
        for title in sorted(has_clause):
            lines.append(f"  ✓ {title}")
    return "\n".join(lines)


def _fmt_amount(val, currency: str = None) -> str:
    """Format with correct currency — USD/EUR/GBP use international, INR uses crore/lakh."""
    if val is None: return "N/A"
    val = float(val)
    cur = (currency or "INR").upper().strip()
    if cur not in ("INR", "RS", "RS.", ""):
        sym = {"USD":"$","EUR":"€","GBP":"£","SGD":"S$","JPY":"¥","AED":"AED "}.get(cur, cur+" ")
        if val >= 1_000_000_000: return f"{sym}{val/1_000_000_000:.2f}B"
        if val >= 1_000_000:     return f"{sym}{val/1_000_000:.1f}M"
        if val >= 1_000:         return f"{sym}{val/1_000:.0f}K"
        return f"{sym}{val:,.0f}"
    # INR — crore/lakh
    if val >= 1_00_00_000: return f"₹{val/1_00_00_000:.2f} Cr"
    if val >= 1_00_000:    return f"₹{val/1_00_000:.1f} L"
    return f"₹{val:,.0f}"
