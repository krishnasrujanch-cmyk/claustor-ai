"""
Regression tests for Judge LLM routing decisions.
Run: pytest app/tests/eval/test_judge_routing.py -v
"""
import pytest
import asyncio
from app.infrastructure.llm.router import get_llm_router
from app.agents.rag.judge_router import judge_classify

# (query, expected_intent, expected_db, expected_db_type)
ROUTING_CASES = [
    # Identifier queries → DB
    ("What is the supplier's GSTIN?",        "structured", True,  "party_identifier"),
    ("What is Meridian's CIN number?",        "structured", True,  "party_identifier"),
    ("List both parties VAT numbers",         "structured", True,  "party_identifier"),
    ("What is the company EIN?",              "structured", True,  "party_identifier"),

    # Metadata queries → DB
    ("When does this contract expire?",       "structured", True,  None),
    ("What is the contract value?",           "structured", True,  None),

    # Content queries → semantic
    ("What are the payment terms?",           "semantic",   False, None),
    ("List all service levels and credits",   "semantic",   False, None),
    ("What happens if we breach payment?",    "semantic",   False, None),
    ("Service level details?",                "semantic",   False, None),
    ("can u share the SLA info",              "semantic",   False, None),
]

@pytest.mark.asyncio
@pytest.mark.parametrize("query,exp_intent,exp_db,exp_type", ROUTING_CASES)
async def test_judge_routing(query, exp_intent, exp_db, exp_type):
    llm = get_llm_router()
    result = await judge_classify(query=query, llm=llm)

    assert result.needs_db == exp_db, \
        f"Query '{query}': expected needs_db={exp_db}, got {result.needs_db}"

    if exp_db:
        assert result.intent == exp_intent, \
            f"Query '{query}': expected intent={exp_intent}, got {result.intent}"

    if exp_type:
        assert result.db_query_type == exp_type, \
            f"Query '{query}': expected db_type={exp_type}, got {result.db_query_type}"
