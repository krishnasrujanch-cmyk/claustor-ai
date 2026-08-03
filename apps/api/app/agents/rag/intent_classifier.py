"""
Intent Classifier v2 — Claustor AI Copilot
Covers all 8 industries: Pharma, BFSI, IT/SaaS, Healthcare,
Manufacturing, Retail, Energy, Legal
"""

from __future__ import annotations
import re
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Structured patterns ───────────────────────────────────────────
STRUCTURED_PATTERNS = [
    r"\bexpir", r"\bdue\b", r"\bdeadline", r"\bmaturing?\b",
    r"\bnext month\b", r"\bthis month\b", r"\bthis week\b", r"\bnext week\b",
    r"\bnext \d+ (days?|weeks?|months?|years?|yrs?)\b",
    r"\bin \d+ (days?|weeks?|months?|years?|yrs?)\b",
    r"\bQ[1-4]\b", r"\bquarter\b", r"\bFY\b", r"\bfinancial year\b",
    r"\bhow many\b", r"\bcount\b", r"\btotal value\b", r"\blist all\b",
    r"\blist of\b", r"\bshow me\b", r"\bshow all\b",
    r"\boverd(ue|raft)", r"\baggregat", r"\baverage risk\b",
    r"\brenew", r"\bauto.?renewal", r"\bupcoming\b",
    r"\babove\b", r"\bbelow\b", r"\bmore than\b", r"\bless than\b",
    r"\bworth\b", r"\bvalue\b", r"\bcrore\b", r"\blakh\b",
    r"\btop \d+\b", r"\bhighest\b", r"\blargest\b", r"\bbiggest\b",
    r"\bby counterparty\b", r"\bby type\b", r"\bby law\b",
    r"\bpending review\b", r"\bapproved\b", r"\brejected\b",
    r"\bstatus\b", r"\bgoverned by\b", r"\bjurisdiction\b",
    r"\bcounterparty\b", r"\bvendor\b", r"\bparty\b",
    r"\bmilestone\b", r"\bpayment schedule\b", r"\bdeadline\b",
    r"\bcompliance\b", r"\bregulatory\b", r"\baudit\b",
    r"\bsorted by\b", r"\border by\b", r"\branked\b",
    r"\bhigh.?risk contracts?\b", r"\blow.?risk contracts?\b", r"\bmedium.?risk contracts?\b",
]

SEMANTIC_PATTERNS = [
    r"\bclause\b", r"\bterm[s]?\b", r"\bsection\b",
    r"\bliabilit", r"\bindemnif", r"\bterminat",
    r"\bnon.?compete", r"\bnda\b", r"\bconfidential",
    r"\bwarrant", r"\bpenalt", r"\bgoverning law\b",
    r"\bintellectual property\b", r"\bip ownership\b",
    r"\broyalt", r"\blicense\b", r"\bsummariz",
    r"\bexplain\b", r"\bwhat (does|is|are)\b",
    r"\btell me about\b", r"\bforce majeure\b",
    r"\barbitration\b", r"\bdispute\b", r"\beslation\b",
    r"\bsource code escrow\b", r"\buptime\b", r"\bsla\b",
    r"\bhipaa\b", r"\bphi\b", r"\bclinical\b",
    r"\bppa\b", r"\bgrid\b", r"\bpurchase commitment\b",
    r"\bexclusivit\b", r"\bfranchise\b", r"\blease\b",
    r"\bretainer\b", r"\bcourt\b",
]

FOLLOWUP_PATTERNS = [
    r"^(this|it|that|the contract|the agreement)\b",
    r"\bmore detail", r"\btell me more\b", r"\belaborat",
    r"\bexpand on\b", r"\bwhat about\b", r"\babt this\b",
    r"\bshare more\b", r"\bgive me more\b", r"\bcan you explain\b",
    r"\bwhat else\b", r"\bgo on\b", r"\bcontinue\b",
]

MISSING_CLAUSE_PATTERNS = [
    r"\bdon.t have\b", r"\bmissing\b", r"\bwithout\b",
    r"\bno .{1,20} clause\b", r"\bnot (contain|include|have)\b",
    r"\black(ing)?\b", r"\babsent\b", r"\bno .{1,20} provision\b",
]

# Query sub-types
AGGREGATION_QUERIES = {
    "count_by_risk":       r"(count|how many).*(risk|high|medium|low)",
    "total_value":         r"total.*(value|amount|worth)",
    "avg_risk":            r"(average|avg).*(risk|score)",
    "count_by_type":       r"(count|how many).*type",
    "count_total":         r"how many.*(contract|agreement)",
    "expiry_list":         r"(expir|due|deadline|matur).*(list|show|what|which|all)",
    "expiry_count":        r"(how many|count).*(expir|due|matur)",
    "high_risk_list":      r"(list|show|which|all|are).*(high risk|risky|high.risk)|(high.?risk).*(contracts?|agreements?)",
    "renewal_list":        r"(auto.?renewal|renew).*(list|which|show|all)",
    "overdue_list":        r"(overdue|past due|expired|lapsed)",
    "top_by_value":        r"top \d+.*(value|worth|amount|contract)",
    "by_counterparty":     r"(contracts?|agreement).*(with|by|from) [A-Z]",
    "by_type":             r"(all |list ).*(nda|msa|sla|vendor|license|lease|loan|employment)",
    "by_status":           r"(pending|approved|rejected|flagged).*(review|contract)",
    "by_jurisdiction":     r"(governed|jurisdiction|law).*(india|us|uk|specific)",
    "value_filter":        r"(above|below|more than|less than|worth|over|under).*(crore|lakh|million|billion|usd|inr|\d+)",
    "milestone_list":      r"(milestone|payment schedule|compliance deadline|regulatory)",
    "high_value":          r"(high.?value|largest|biggest|most valuable)",
    "pending_review":      r"(pending|awaiting).*(review|approval|legal)",
}


@dataclass
class QueryIntent:
    intent:         str
    sub_type:       Optional[str]   = None
    timeframe:      Optional[str]   = None
    date_start:     Optional[date]  = None
    date_end:       Optional[date]  = None
    is_followup:    bool            = False
    confidence:     float           = 0.5
    reasoning:      str             = ""
    filters:        dict            = field(default_factory=dict)


def classify_intent(query: str, has_history: bool = False) -> QueryIntent:
    q = query.lower().strip()

    # ── Followup detection ──
    is_followup = (
        has_history and
        len(q.split()) < 10 and
        any(re.search(p, q) for p in FOLLOWUP_PATTERNS)
    )

    # ── Missing clause ──
    if any(re.search(p, q) for p in MISSING_CLAUSE_PATTERNS):
        return QueryIntent(
            intent="missing", sub_type="missing_clause",
            is_followup=is_followup, confidence=0.9,
            reasoning="Query asks about missing/absent clauses"
        )

    # ── Sub-type detection ──
    sub_type = None
    for name, pattern in AGGREGATION_QUERIES.items():
        if re.search(pattern, q):
            sub_type = name
            break

    # ── Score structured vs semantic ──
    s_score = sum(1 for p in STRUCTURED_PATTERNS if re.search(p, q))
    v_score = sum(1 for p in SEMANTIC_PATTERNS  if re.search(p, q))

    # ── Timeframe extraction ──
    timeframe, date_start, date_end = _extract_timeframe(q)
    if timeframe:
        s_score += 3

    # ── Extract additional filters ──
    filters = _extract_filters(q)

    # ── Determine intent ──
    if is_followup:
        intent, confidence = "followup", 0.85
        reasoning = "Short vague query with prior conversation context"
    elif s_score > 0 and v_score == 0:
        intent, confidence = "structured", min(0.95, 0.6 + s_score * 0.1)
        reasoning = f"Matched {s_score} structured patterns"
    elif v_score > 0 and s_score == 0:
        intent, confidence = "semantic", min(0.95, 0.6 + v_score * 0.1)
        reasoning = f"Matched {v_score} semantic patterns"
    elif s_score > 0 and v_score > 0:
        intent, confidence = "hybrid", 0.75
        reasoning = f"Mixed: {s_score} structured + {v_score} semantic"
    else:
        intent, confidence = "semantic", 0.5
        reasoning = "No strong signal — defaulting to semantic"

    return QueryIntent(
        intent=intent, sub_type=sub_type,
        timeframe=timeframe, date_start=date_start, date_end=date_end,
        is_followup=is_followup, confidence=confidence,
        reasoning=reasoning, filters=filters,
    )


def _extract_timeframe(q: str):
    today = date.today()
    current_year = today.year

    # Next/this N years/months/weeks/days
    m = re.search(r"next (\d+) (?:years?|yrs?)", q)
    if m:
        n = int(m.group(1))
        return f"next_{n}_years", today, date(today.year+n, today.month, today.day)

    m = re.search(r"next (\d+) months?", q)
    if m:
        n = int(m.group(1))
        end = today + timedelta(days=n*30)
        return f"next_{n}_months", today, end

    m = re.search(r"next (\d+) (?:days?|weeks?)", q)
    if m:
        n = int(m.group(1))
        unit = "days" if "day" in q else "weeks"
        days = n if unit == "days" else n * 7
        return f"next_{n}_{unit}", today, today + timedelta(days=days)

    m = re.search(r"in (\d+) (?:days?|weeks?|months?)", q)
    if m:
        n = int(m.group(1))
        if "day" in q: days = n
        elif "week" in q: days = n * 7
        else: days = n * 30
        return f"in_{n}", today, today + timedelta(days=days)

    # Standard timeframes
    if "next month" in q:
        start = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return "next_month", start, end

    if "this month" in q:
        start = today.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return "this_month", start, end

    if "next week" in q:
        start = today - timedelta(days=today.weekday()) + timedelta(days=7)
        return "next_week", start, start + timedelta(days=6)

    if "this week" in q:
        start = today - timedelta(days=today.weekday())
        return "this_week", start, start + timedelta(days=6)

    if "next year" in q:
        ny = current_year + 1
        return "next_year", date(ny, 1, 1), date(ny, 12, 31)

    if "this year" in q:
        return "this_year", date(current_year, 1, 1), date(current_year, 12, 31)

    # Quarter detection: Q1/Q2/Q3/Q4 [YEAR]
    m = re.search(r"q([1-4])(?:\s+(\d{4}))?", q)
    if m:
        qn = int(m.group(1))
        yr = int(m.group(2)) if m.group(2) else current_year
        q_start_month = (qn - 1) * 3 + 1
        q_end_month = qn * 3
        start = date(yr, q_start_month, 1)
        if q_end_month == 12:
            end = date(yr, 12, 31)
        else:
            end = date(yr, q_end_month + 1, 1) - timedelta(days=1)
        return f"Q{qn}_{yr}", start, end

    # Indian Financial Year: FY2026-27 or FY26-27 or "this FY" or "next FY"
    m = re.search(r"fy\s*(\d{2,4})[-–](\d{2,4})", q)
    if m:
        yr_start = int(m.group(1))
        if yr_start < 100:
            yr_start += 2000
        return f"FY{yr_start}", date(yr_start, 4, 1), date(yr_start+1, 3, 31)

    if "this fy" in q or "current fy" in q or "this financial year" in q:
        fy_start = current_year if today.month >= 4 else current_year - 1
        return f"FY{fy_start}", date(fy_start, 4, 1), date(fy_start+1, 3, 31)

    if "next fy" in q or "next financial year" in q:
        fy_start = (current_year if today.month >= 4 else current_year - 1) + 1
        return f"FY{fy_start}", date(fy_start, 4, 1), date(fy_start+1, 3, 31)

    # Specific year: "expiring in 2028"
    m = re.search(r"\b(20\d{2})\b", q)
    if m and any(k in q for k in ["expir","due","matur","renew"]):
        yr = int(m.group(1))
        return f"year_{yr}", date(yr, 1, 1), date(yr, 12, 31)

    # "Soon" = next 90 days
    if "soon" in q or "upcoming" in q:
        return "soon", today, today + timedelta(days=90)

    # Overdue
    if "overdue" in q or "past due" in q or "lapsed" in q:
        return "overdue", date(2000, 1, 1), today - timedelta(days=1)

    return None, None, None


def _extract_filters(q: str) -> dict:
    """Extract additional structured filters from query."""
    filters = {}

    # Value filters (Indian + international)
    # crore: 1 crore = 10,000,000
    m = re.search(r"(?:above|more than|over|worth|>\s*)(\d+(?:\.\d+)?)\s*crore", q)
    if m: filters["min_value"] = float(m.group(1)) * 10_000_000

    m = re.search(r"(?:below|less than|under|<\s*)(\d+(?:\.\d+)?)\s*crore", q)
    if m: filters["max_value"] = float(m.group(1)) * 10_000_000

    # lakh: 1 lakh = 100,000
    m = re.search(r"(?:above|more than|over|worth|>\s*)(\d+(?:\.\d+)?)\s*lakh", q)
    if m: filters["min_value"] = float(m.group(1)) * 100_000

    m = re.search(r"(?:below|less than|under|<\s*)(\d+(?:\.\d+)?)\s*lakh", q)
    if m: filters["max_value"] = float(m.group(1)) * 100_000

    # million/billion
    m = re.search(r"(?:above|more than|over|>\s*)(\d+(?:\.\d+)?)\s*million", q)
    if m: filters["min_value"] = float(m.group(1)) * 1_000_000

    m = re.search(r"(?:above|more than|over|>\s*)(\d+(?:\.\d+)?)\s*billion", q)
    if m: filters["min_value"] = float(m.group(1)) * 1_000_000_000

    # Raw number (USD/INR)
    m = re.search(r"(?:above|more than|over|>\s*)[\$₹]?\s*(\d[\d,]+)", q)
    if m and "min_value" not in filters:
        filters["min_value"] = float(m.group(1).replace(",",""))

    # Top N
    m = re.search(r"top (\d+)", q)
    if m: filters["top_n"] = int(m.group(1))

    # Risk level
    if "high risk" in q or "high-risk" in q: filters["risk_level"] = "high"
    elif "medium risk" in q: filters["risk_level"] = "medium"
    elif "low risk" in q: filters["risk_level"] = "low"

    # Risk score threshold
    m = re.search(r"risk (?:score )?(?:above|>|more than) (\d+)", q)
    if m: filters["min_risk_score"] = int(m.group(1))

    # Contract type
    type_map = {
        "nda": "NDA", "msa": "MSA", "sla": "SLA",
        "vendor": "Vendor", "license": "License",
        "lease": "Lease", "loan": "Loan",
        "employment": "Employment", "franchise": "Franchise",
        "ppa": "PPA", "retainer": "Retainer",
    }
    for kw, ct in type_map.items():
        if kw in q: filters["contract_type"] = ct; break

    # Status
    if "pending review" in q: filters["status"] = "pending_review"
    elif "approved" in q and "contract" in q: filters["review_status"] = "approved"
    elif "rejected" in q: filters["review_status"] = "rejected"
    elif "flagged" in q: filters["flagged"] = True

    # Governing law/jurisdiction
    juris_map = {
        "india": "India", "indian law": "India",
        "us law": "United States", "american law": "United States",
        "uk law": "United Kingdom", "english law": "United Kingdom",
        "delaware": "Delaware", "singapore": "Singapore",
    }
    for kw, jv in juris_map.items():
        if kw in q: filters["governing_law"] = jv; break

    # Counterparty name (capitalized word after "with"/"from"/"by")
    m = re.search(r"(?:with|from|by|vendor)\s+([A-Z][a-zA-Z\s]{2,30}?)(?:\s|$)", q)
    if m: filters["counterparty"] = m.group(1).strip()

    # Auto-renewal
    if "auto.?renewal" in q or "auto renew" in q:
        filters["auto_renewal"] = True

    return filters
