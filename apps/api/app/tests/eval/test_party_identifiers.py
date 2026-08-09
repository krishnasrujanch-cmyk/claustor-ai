"""
Regression tests for party identifier extraction.
Run: pytest app/tests/eval/test_party_identifiers.py -v
"""
import pytest
import asyncio
from app.infrastructure.identifiers.party_extractor import (
    extract_party_identifiers, build_identifier_summary
)

# Known test cases — add more as you verify new contracts
CASES = [
    {
        "name": "India-India (Northwind/Meridian)",
        "text": """BETWEEN
Northwind Cloud Technologies Private Limited
CIN U72900KA2016PTC088214 | GSTIN 29AAJCN4417K1ZP
(Supplier)
AND
Meridian Trust Bank Limited
CIN L65190MH1994PLC079214 | GSTIN 27AABCM8821L1Z4
(Customer)""",
        "expected_parties": 2,
        "expected_ids": {"29AAJCN4417K1ZP", "27AABCM8821L1Z4",
                         "U72900KA2016PTC088214", "L65190MH1994PLC079214"},
        "expected_roles": {"Supplier", "Customer"},
    },
    {
        "name": "UK-India cross-border",
        "text": """Nexus ITO Group Pvt. Ltd.
GSTIN: 33AABCN1234M1ZX (Service Provider)
AND
BritanniaRetail Holdings Plc
Company No: 04123456 VAT: GB 123 4567 89 (Client)""",
        "expected_parties": 2,
        "expected_ids": {"33AABCN1234M1ZX", "04123456"},
        "expected_roles": {"Service Provider", "Client"},
    },
    {
        "name": "US-EU",
        "text": """CloudForce Inc. EIN: 47-1234567 (Licensor)
Deutsche Finanz GmbH VAT: DE123456789 (Licensee)""",
        "expected_parties": 2,
        "expected_ids": {"47-1234567", "DE123456789"},
        "expected_roles": {"Licensor", "Licensee"},
    },
    {
        "name": "Multi-party India (3 parties)",
        "text": """Reliance Digital Ventures Private Limited
GSTIN: 27AABCR1234F1ZX (Principal)
Tata Consultancy Services Limited
GSTIN: 27AABCT0942F1ZW (Service Provider)
HDFC Bank Limited
GSTIN: 27AAACH2702H1ZM (Escrow Agent)""",
        "expected_parties": 3,
        "expected_ids": {"27AABCR1234F1ZX", "27AABCT0942F1ZW", "27AAACH2702H1ZM"},
        "expected_roles": {"Principal", "Service Provider", "Escrow Agent"},
    },
]

@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
async def test_party_extraction(case):
    result = await extract_party_identifiers(case["text"])

    assert len(result) == case["expected_parties"], \
        f"Expected {case['expected_parties']} parties, got {len(result)}"

    all_ids = {i["value"] for p in result for i in p["identifiers"]}
    for expected_id in case["expected_ids"]:
        assert expected_id in all_ids, \
            f"Expected identifier {expected_id} not found. Got: {all_ids}"

    all_roles = {p["role"] for p in result}
    for role in case["expected_roles"]:
        assert role in all_roles, \
            f"Expected role '{role}' not found. Got: {all_roles}"


@pytest.mark.asyncio
async def test_summary_text_generated():
    result = await extract_party_identifiers(CASES[0]["text"])
    summary = build_identifier_summary(result)
    assert "PARTIES & REGISTRATION IDENTIFIERS" in summary
    assert "29AAJCN4417K1ZP" in summary
    assert "Northwind" in summary
