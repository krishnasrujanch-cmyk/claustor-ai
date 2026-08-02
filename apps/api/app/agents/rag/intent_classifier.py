"""
Intent Classifier for Claustor AI Copilot.
Classifies user queries into routing categories before RAG/DB lookup.

Intent Types:
  structured  → Pure DB query (expiry, counts, lists, aggregations)
  semantic    → Pure vector search (clause details, summaries, terms)
  hybrid      → Both DB + vector (e.g. "risky expiring contracts")
  followup    → Continue previous conversation context
  missing     → "which contracts don't have X clause" (metadata query)
"""

from __future__ import annotations
import json
import re
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Keyword-based fast pre-classifier (no LLM cost) ──────────────────────────

STRUCTURED_PATTERNS = [
    r"\bexpir",
    r"\bdue\b",
    r"\bdeadline",
    r"\bnext month\b",
    r"\bthis month\b",
    r"\bthis week\b",
    r"\bnext week\b",
    r"\bin \d+ days\b",
    r"\bhow many\b",
    r"\bcount\b",
    r"\btotal value\b",
    r"\blist all\b",
    r"\blist of\b",
    r"\ball contracts\b",
    r"\boverd(ue|raft)",
    r"\baggregat",
    r"\baverage risk\b",
    r"\brightexpir",
    r"\brenew",
    r"\bauto.?renewal",
    r"\bupcoming\b",
]

SEMANTIC_PATTERNS = [
    r"\bclause\b",
    r"\bterm[s]?\b",
    r"\bsection\b",
    r"\bpayment\b",
    r"\bliabilit",
    r"\bindemnif",
    r"\bterminat",
    r"\bnon.?compete",
    r"\bnda\b",
    r"\bconfidential",
    r"\bwarrant",
    r"\bpenalt",
    r"\bgoverning law\b",
    r"\bjurisdiction\b",
    r"\bintellectual property\b",
    r"\bip ownership\b",
    r"\broyalt",
    r"\blicense\b",
    r"\bsummariz",
    r"\bexplain\b",
    r"\bwhat (does|is|are)\b",
    r"\btell me about\b",
]

FOLLOWUP_PATTERNS = [
    r"^(this|it|that|the contract|the agreement)\b",
    r"\bmore detail",
    r"\btell me more\b",
    r"\belaborat",
    r"\bexpand on\b",
    r"\bwhat about\b",
    r"\babt this\b",
    r"\bshare more\b",
    r"\bgive me more\b",
    r"\bcan you explain\b",
    r"\bwhat else\b",
]

MISSING_CLAUSE_PATTERNS = [
    r"\bdon.t have\b",
    r"\bmissing\b",
    r"\bwithout\b",
    r"\bno .{1,20} clause\b",
    r"\bnot (contain|include|have)\b",
    r"\black(ing)?\b",
    r"\babsent\b",
]

AGGREGATION_QUERIES = {
    "count_by_risk":       r"(count|how many).*(risk|high|medium|low)",
    "total_value":         r"total.*(value|amount|worth)",
    "avg_risk":            r"(average|avg).*(risk|score)",
    "count_by_type":       r"(count|how many).*type",
    "expiry_list":         r"(expir|due|deadline).*(list|show|what|which)",
    "expiry_count":        r"(how many|count).*(expir|due)",
    "high_risk_list":      r"(list|show|which).*(high risk|risky)",
    "renewal_list":        r"(auto.?renewal|renew).*(list|which|show)",
    "overdue_list":        r"(overdue|past due|expired)",
}


@dataclass
class QueryIntent:
    intent:          str            # structured | semantic | hybrid | followup | missing
    sub_type:        Optional[str]  # e.g. expiry_list, count_by_risk
    timeframe:       Optional[str]  # next_month, this_week, custom
    date_start:      Optional[date]
    date_end:        Optional[date]
    is_followup:     bool
    confidence:      float          # 0-1
    reasoning:       str


def classify_intent(query: str, has_history: bool = False) -> QueryIntent:
    """
    Fast keyword-based intent classifier.
    No LLM call — deterministic and instant.
    """
    q = query.lower().strip()
    
    # ── Followup detection ──
    is_followup = (
        has_history and
        len(q.split()) < 10 and
        any(re.search(p, q) for p in FOLLOWUP_PATTERNS)
    )
    
    # ── Sub-type detection ──
    sub_type = None
    for name, pattern in AGGREGATION_QUERIES.items():
        if re.search(pattern, q):
            sub_type = name
            break
    
    # ── Missing clause detection ──
    if any(re.search(p, q) for p in MISSING_CLAUSE_PATTERNS):
        return QueryIntent(
            intent="missing", sub_type="missing_clause",
            timeframe=None, date_start=None, date_end=None,
            is_followup=is_followup, confidence=0.9,
            reasoning="Query asks about missing/absent clauses"
        )
    
    # ── Score structured vs semantic ──
    s_score = sum(1 for p in STRUCTURED_PATTERNS if re.search(p, q))
    v_score = sum(1 for p in SEMANTIC_PATTERNS  if re.search(p, q))
    
    # ── Timeframe extraction ──
    timeframe, date_start, date_end = _extract_timeframe(q)
    if timeframe:
        s_score += 2  # boost structured score for time queries
    
    # ── Determine intent ──
    if is_followup:
        intent = "followup"
        confidence = 0.85
        reasoning = "Short query with prior conversation context"
    elif s_score > 0 and v_score == 0:
        intent = "structured"
        confidence = min(0.95, 0.6 + s_score * 0.1)
        reasoning = f"Matched {s_score} structured patterns"
    elif v_score > 0 and s_score == 0:
        intent = "semantic"
        confidence = min(0.95, 0.6 + v_score * 0.1)
        reasoning = f"Matched {v_score} semantic patterns"
    elif s_score > 0 and v_score > 0:
        intent = "hybrid"
        confidence = 0.75
        reasoning = f"Mixed: {s_score} structured + {v_score} semantic patterns"
    else:
        # Default to semantic for unknown queries
        intent = "semantic"
        confidence = 0.5
        reasoning = "No strong signal — defaulting to semantic search"
    
    logger.info("intent_classified", extra={
        "q": query[:60], "intent": intent, "sub_type": sub_type,
        "s_score": s_score, "v_score": v_score, "confidence": confidence,
    })
    
    return QueryIntent(
        intent=intent, sub_type=sub_type,
        timeframe=timeframe, date_start=date_start, date_end=date_end,
        is_followup=is_followup, confidence=confidence, reasoning=reasoning,
    )


def _extract_timeframe(q: str):
    """Extract date range from natural language."""
    today = date.today()
    
    if "next month" in q:
        start = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return "next_month", start, end
    
    if "this month" in q:
        start = today.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return "this_month", start, end
    
    if "this week" in q:
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return "this_week", start, end
    
    if "next week" in q:
        start = today - timedelta(days=today.weekday()) + timedelta(days=7)
        end = start + timedelta(days=6)
        return "next_week", start, end
    
    if "next 30 days" in q or "30 days" in q:
        return "next_30_days", today, today + timedelta(days=30)
    
    if "next 90 days" in q or "90 days" in q or "quarter" in q:
        return "next_90_days", today, today + timedelta(days=90)
    
    if "this year" in q:
        return "this_year", today.replace(month=1, day=1), today.replace(month=12, day=31)
    
    if "overdue" in q or "past due" in q or "expired" in q:
        return "overdue", date(2000, 1, 1), today - timedelta(days=1)
    
    # Look for "in N days"
    m = re.search(r"in (\d+) days", q)
    if m:
        n = int(m.group(1))
        return f"next_{n}_days", today, today + timedelta(days=n)
    
    return None, None, None
