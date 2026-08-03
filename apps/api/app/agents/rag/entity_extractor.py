"""
LLM Entity Extractor for Claustor AI Copilot.
Extracts structured filters from natural language queries.
Fast, cheap — uses smallest Groq model.
"""

from __future__ import annotations
import json
import logging
import re
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a contract query parser. Extract structured filters from the user query.

Today's date: {today}
Current Financial Year (India): {fy_start} to {fy_end}

Query: "{query}"

Return ONLY valid JSON with these fields (use null if not mentioned):
{{
  "counterparty": "company/party name if mentioned, else null",
  "contract_type": "NDA|MSA|SLA|Employment|Vendor|License|Lease|Loan|Franchise|PPA|Retainer|Other or null",
  "min_value": "minimum contract value as number (convert crore×10M, lakh×100K), null if not mentioned",
  "max_value": "maximum contract value as number, null if not mentioned",
  "date_start": "YYYY-MM-DD start of date range, null if not mentioned",
  "date_end": "YYYY-MM-DD end of date range, null if not mentioned",
  "risk_level": "high|medium|low or null",
  "min_risk_score": "minimum risk score as integer (0-100), null if not mentioned",
  "governing_law": "jurisdiction/country if mentioned, null if not mentioned",
  "status": "pending|approved|rejected|flagged or null",
  "top_n": "number if user wants top N results, null if not mentioned",
  "auto_renewal": "true if user asks about auto-renewal contracts, else null",
  "intent": "expiry_list|count|value_query|risk_query|type_filter|party_filter|milestone|missing_clause|general"
}}

Rules:
- Dates: "next month"=next calendar month, "this FY"=Apr {fy_yr}-Mar {fy_yr_end}, "Q3 2027"=Jul-Sep 2027
- Values: "1 crore"=10000000, "50 lakh"=5000000, "1 million"=1000000, "$500K"=500000
- "expiring soon"=next 90 days, "overdue"=before today
- For counterparty: extract exact company name mentioned
- Return null for any field not clearly mentioned in query
Return ONLY the JSON object, no explanation."""


async def extract_query_entities(
    query: str,
    llm,
) -> dict:
    """
    Use LLM to extract structured entities from natural language query.
    Falls back to empty dict on failure.
    """
    today = date.today()
    fy_yr = today.year if today.month >= 4 else today.year - 1
    fy_start = date(fy_yr, 4, 1)
    fy_end = date(fy_yr + 1, 3, 31)

    prompt = EXTRACTION_PROMPT.format(
        today=today.isoformat(),
        fy_start=fy_start.isoformat(),
        fy_end=fy_end.isoformat(),
        fy_yr=fy_yr,
        fy_yr_end=fy_yr + 1,
        query=query,
    )

    try:
        from app.infrastructure.llm.base import AgentRole, LLMMessage
        response = await llm.complete(
            messages=[
                LLMMessage(role="system", content="Return only valid JSON. No markdown, no explanation."),
                LLMMessage(role="user",   content=prompt),
            ],
            role=AgentRole.EXTRACTOR,
            json_mode=True,
        )
        raw = response.content.strip()
        # Strip markdown if present
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        entities = json.loads(raw)

        # Normalize
        result = {}
        if entities.get("counterparty"):
            result["counterparty"] = str(entities["counterparty"]).strip()
        if entities.get("contract_type"):
            result["contract_type"] = str(entities["contract_type"]).strip()
        if entities.get("min_value") is not None:
            result["min_value"] = float(entities["min_value"])
        if entities.get("max_value") is not None:
            result["max_value"] = float(entities["max_value"])
        if entities.get("date_start"):
            result["date_start"] = date.fromisoformat(str(entities["date_start"]))
        if entities.get("date_end"):
            result["date_end"] = date.fromisoformat(str(entities["date_end"]))
        if entities.get("risk_level"):
            result["risk_level"] = str(entities["risk_level"]).lower()
        if entities.get("min_risk_score") is not None:
            result["min_risk_score"] = int(entities["min_risk_score"])
        if entities.get("governing_law"):
            result["governing_law"] = str(entities["governing_law"]).strip()
        if entities.get("status"):
            result["status"] = str(entities["status"]).lower()
        if entities.get("top_n") is not None:
            result["top_n"] = int(entities["top_n"])
        if entities.get("auto_renewal"):
            result["auto_renewal"] = True
        if entities.get("intent"):
            result["llm_intent"] = str(entities["intent"])

        logger.info(f"entity_extraction: query={query[:50]!r} → {result}")
        return result

    except Exception as e:
        logger.warning(f"entity_extraction_failed: {e}")
        return {}


def merge_filters(keyword_filters: dict, llm_filters: dict) -> dict:
    """Merge keyword-extracted filters with LLM-extracted filters. LLM wins on conflicts."""
    merged = dict(keyword_filters)
    for k, v in llm_filters.items():
        if v is not None and k != "llm_intent":
            merged[k] = v
    return merged


def llm_intent_to_sub_type(llm_intent: str) -> str:
    """Map LLM intent string to our sub_type."""
    mapping = {
        "expiry_list":    "expiry_list",
        "count":          "count_total",
        "value_query":    "total_value",
        "risk_query":     "count_by_risk",
        "type_filter":    "by_type",
        "party_filter":   "by_counterparty",
        "milestone":      "milestone_list",
        "missing_clause": "missing_clause",
    }
    return mapping.get(llm_intent, None)
