"""
Claustor AI — Judge-based Intent Router
Single LLM call (Anthropic/Groq) for:
  1. Intent classification
  2. Entity extraction  
  3. Query rewriting for better retrieval
  4. Routing decision (DB/vector/hybrid)

Replaces keyword-based intent_classifier.py
Falls back to keyword classifier on failure.
"""

from __future__ import annotations
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """You are a contract intelligence routing system. Analyze the user query and return routing JSON.

TODAY: {today}
CURRENT FY (India): {fy_start} to {fy_end}
RECENT CONVERSATION:
{history}

USER QUERY: "{query}"

Classify and extract:

INTENT OPTIONS:
ROUTING RULES:

ALWAYS needs_vector=true (semantic search in contract text):
- ANY question about clause content: payment, termination, liability, IP,
  confidentiality, indemnification, warranty, audit, force majeure, governing law,
  dispute resolution, representations, obligations, rights, restrictions
- ANY schedule/table/annexure: payment schedule, milestone, royalty rate,
  sales commitments, fee schedule, SLA, KPI, deliverables, penalties, patent schedule
- ANY vague/short query about contract data: "sales data", "payment info",
  "share X", "tell me about X", "what about X", "details on X", "show me X"
- ANY question with "what does it say", "what are the terms", "explain"
- ANY followup: "tell me more", "explain that", "what does that mean"
- Multilingual queries about contract content

ONLY needs_db=true (pure structured query — NO contract text needed):
- Party registration/tax identifiers: GSTIN, CIN, PAN, TAN, VAT, EIN, DUNS, UEN, ABN, ACN, TRN, IBAN, SWIFT, Company No, registration number, tax ID
  → needs_db=true, needs_vector=false, db_query_type="party_identifier"
  Examples: "supplier GSTIN", "what is the CIN", "party registration number", "company VAT number"
- Contract metadata ONLY: expiry date, contract value, counterparty name,
  contract type, risk level, risk score, auto-renewal flag, contract status
- Cross-contract aggregations: count, list, filter, "show contracts where..."
- "how many", "which contracts", "list all contracts", "contracts expiring"

KEY RULE: If a specific contract_id is selected AND the query asks about
content/data/clauses/schedules → ALWAYS needs_vector=true, needs_db=false
Only use needs_db=true when the answer comes from contract metadata fields,
NOT from the contract text itself.

Return ONLY this JSON (no markdown):
{{
  "intent": "structured|semantic|hybrid|followup|missing",
  "needs_db": true/false,
  "needs_vector": true/false,
  "complexity": "simple|medium|complex",
  "is_followup": true/false,
  "db_query_type": "expiry_list|count_total|value_query|risk_query|type_filter|party_filter|milestone|renewal_list|overdue_list|value_filter|avg_risk|count_by_risk|party_identifier|null",
  "filters": {{
    "counterparty": "exact company name or null",
    "contract_type": "NDA|MSA|SLA|Employment|Vendor|License|Lease|Loan|Franchise|PPA|Retainer|null",
    "risk_level": "high|medium|low|null",
    "min_risk_score": "0-100 or null",
    "min_value": "number (convert 1 crore=10000000, 1 lakh=100000, 1M=1000000) or null",
    "max_value": "number or null",
    "date_start": "YYYY-MM-DD or null",
    "date_end": "YYYY-MM-DD or null",
    "governing_law": "jurisdiction or null",
    "auto_renewal": "true or null",
    "top_n": "number or null",
    "status": "pending|approved|rejected|flagged|null",
    "missing_clause": "clause_type or null"
  }},
  "rewritten_query": "Rewrite the query for better vector search. Expand abbreviations, add related legal terms. Keep it under 100 words.",
  "reasoning": "One line why you chose this intent"

COMPLEXITY RULES:
- "simple":  single fact, single clause, direct lookup, metadata query
  e.g. "GSTIN", "CIN", "PAN", "VAT number", "company registration", "tax ID", "EIN", "UEN", "ABN" → needs_db=true, needs_vector=false, db_query_type="party_identifier"
- "when does this expire", "what is the value", "list payment terms"
- "medium":  multi-clause, comparison, summary, explanation needed
  e.g. "explain the termination conditions", "what are the key risks"
- "complex": multi-contract reasoning, legal analysis, cross-reference chains,
  ambiguous language, risk assessment, "what happens if X AND Y", 
  comparative legal opinion
  e.g. "is this indemnification clause fair", "what if we breach payment AND miss milestone"
}}"""


@dataclass
class JudgeResult:
    intent:         str             = "semantic"
    complexity:     str             = "simple"  # simple | medium | complex
    needs_db:       bool            = False
    needs_vector:   bool            = True
    is_followup:    bool            = False
    db_query_type:  Optional[str]   = None
    filters:        dict            = field(default_factory=dict)
    rewritten_query: str            = ""
    reasoning:      str             = ""
    fallback_used:  bool            = False


async def judge_classify(
    query: str,
    llm,
    history_turns: list = None,
    org_id: Optional[UUID] = None,
    contract_meta: dict = None,
) -> JudgeResult:
    """
    Use Judge LLM to classify intent, extract entities, rewrite query.
    Falls back to keyword classifier on failure.
    """
    today = date.today()
    fy_yr = today.year if today.month >= 4 else today.year - 1
    fy_start = date(fy_yr, 4, 1)
    fy_end = date(fy_yr + 1, 3, 31)

    # Format recent history
    history_text = "None"
    if history_turns:
        lines = []
        for turn in history_turns[-4:]:  # last 2 pairs
            role = turn[0] if isinstance(turn, (list, tuple)) else turn.get("role", "")
            content = turn[1] if isinstance(turn, (list, tuple)) else turn.get("content", "")
            lines.append(f"{role.upper()}: {str(content)[:150]}")
        history_text = "\n".join(lines) or "None"

    # Build party context for generic reference resolution
    party_context = ""
    if contract_meta:
        cp = contract_meta.get("counterparty", "")
        ct = contract_meta.get("contract_type", "")
        title = contract_meta.get("title", "")
        if cp or ct:
            party_context = f"""
CONTRACT CONTEXT:
- Title: {title}
- Counterparty/Supplier: {cp}
- Type: {ct}

When user mentions "supplier", "vendor", "service provider" → refers to {cp or "the supplier"}
When user mentions "customer", "client", "buyer" → refers to the other party
Include actual company name in rewritten_query when resolving generic party references.
"""

    prompt = JUDGE_PROMPT.format(
        today=today.isoformat(),
        fy_start=fy_start.isoformat(),
        fy_end=fy_end.isoformat(),
        history=history_text,
        query=query,
    )
    if party_context:
        prompt = party_context + "\n" + prompt

    try:
        from app.infrastructure.llm.base import AgentRole, LLMMessage
        response = await llm.complete(
            messages=[
                LLMMessage(role="system", content="Return only valid JSON. No markdown, no explanation."),
                LLMMessage(role="user", content=prompt),
            ],
            role=AgentRole.JUDGE,
            json_mode=True,
        )
        raw = response.content.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)

        # Parse filters
        filters = {}
        raw_filters = data.get("filters", {})
        if isinstance(raw_filters, dict):
            for k, v in raw_filters.items():
                if v and v != "null":
                    if k in ("min_value", "max_value") and v:
                        try: filters[k] = float(v)
                        except: pass
                    elif k == "min_risk_score" and v:
                        try: filters[k] = int(v)
                        except: pass
                    elif k == "top_n" and v:
                        try: filters[k] = int(v)
                        except: pass
                    elif k in ("date_start", "date_end") and v:
                        try: filters[k] = date.fromisoformat(str(v))
                        except: pass
                    elif k == "auto_renewal" and v:
                        filters[k] = True
                    elif v not in (None, "null", ""):
                        filters[k] = v

        result = JudgeResult(
            intent          = data.get("intent", "semantic"),
            needs_db        = bool(data.get("needs_db", False)),
            needs_vector    = bool(data.get("needs_vector", True)),
            is_followup     = bool(data.get("is_followup", False)),
            db_query_type   = data.get("db_query_type") or None,
            filters         = filters,
            rewritten_query = data.get("rewritten_query", query) or query,
            reasoning       = data.get("reasoning", ""),
            fallback_used   = False,
            complexity      = data.get("complexity", "simple"),
        )

        # Fix null db_query_type
        if result.db_query_type in ("null", "None", ""):
            result.db_query_type = None

        logger.info(
            f"judge_classified: intent={result.intent} db={result.needs_db} "
            f"vec={result.needs_vector} db_type={result.db_query_type} "
            f"filters={result.filters} q={query[:40]!r}"
        )
        return result

    except Exception as e:
        logger.warning(f"judge_failed: {e} — falling back to keyword classifier")
        return _keyword_fallback(query, fallback_used=True)


def _keyword_fallback(query: str, fallback_used: bool = True) -> JudgeResult:
    """Keyword-based fallback when Judge LLM fails."""
    from app.agents.rag.intent_classifier import classify_intent
    kw = classify_intent(query, has_history=False)

    return JudgeResult(
        intent          = kw.intent,
        needs_db        = kw.intent in ("structured", "hybrid"),
        needs_vector    = kw.intent in ("semantic", "hybrid", "followup"),
        is_followup     = kw.is_followup,
        db_query_type   = kw.sub_type,
        filters         = kw.filters,
        rewritten_query = query,
        reasoning       = f"keyword fallback: {kw.reasoning}",
        fallback_used   = fallback_used,
    )
