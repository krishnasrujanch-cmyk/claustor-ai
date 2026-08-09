"""
Model integrity tests — catch wrong field placement.
Run: pytest app/tests/eval/test_model_integrity.py -v
"""
import pytest
from app.domain.models.models import Contract, Clause, Organisation, ContractChunk

def test_party_identifiers_only_on_contract():
    """party_identifiers must be on Contract only — not Clause or Organisation."""
    assert hasattr(Contract, "party_identifiers"), \
        "Contract must have party_identifiers"
    assert not hasattr(Clause, "party_identifiers"), \
        "Clause must NOT have party_identifiers"
    assert not hasattr(Organisation, "party_identifiers"), \
        "Organisation must NOT have party_identifiers"

def test_required_contract_fields():
    """All required contract fields must exist."""
    required = [
        "party_identifiers", "missing_clauses", "detected_language",
        "risk_score", "risk_level", "status", "counterparty",
        "contract_type", "governing_law", "expiry_date", "contract_value",
    ]
    for field in required:
        assert hasattr(Contract, field), f"Contract missing field: {field}"

def test_required_clause_fields():
    """All required clause fields must exist."""
    required = [
        "clause_type", "risk_score", "risk_level", "playbook_match",
        "deviation_from_std", "adjusted_risk", "industry_weight",
        "related_clauses", "cross_references",
    ]
    for field in required:
        assert hasattr(Clause, field), f"Clause missing field: {field}"

def test_required_org_fields():
    """All required org fields must exist."""
    required = [
        "plan", "gstin", "address", "phone", "website",
        "max_contracts", "max_queries_mo", "max_users",
        "contracts_used", "queries_used",
    ]
    for field in required:
        assert hasattr(Organisation, field), f"Organisation missing field: {field}"
