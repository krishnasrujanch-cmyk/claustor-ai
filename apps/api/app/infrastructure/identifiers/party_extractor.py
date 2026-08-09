"""
Claustor AI — Party Identifier Extractor (Option B)
Uses LLM to extract party names + registration numbers from
first pages of contract — handles any PDF layout.
"""
from __future__ import annotations
import json
import re
import structlog
from typing import Optional

logger = structlog.get_logger()

PARTY_EXTRACTION_PROMPT = """You are a legal contract parser. Extract ALL parties and their registration/tax identifiers.

CONTRACT TEXT (first pages):
{text}

Extract ALL identifier types including:
    - GSTIN (IN): Goods and Services Tax Identification Number
    - CIN (IN): Company Identification Number
    - PAN (IN): Permanent Account Number
    - TAN (IN): Tax Deduction Account Number
    - DIN (IN): Director Identification Number
    - IEC (IN): Importer Exporter Code
    - LLPIN (IN): LLP Identification Number
    - UDYAM (IN): MSME Registration Number
    - VAT (GB): UK VAT Registration Number
    - Company No (GB): UK Companies House Registration
    - CRN (GB): UK Company Registration Number
    - EIN (US): Employer Identification Number
    - DUNS (US): Data Universal Numbering System
    - CAGE (US): SAM/CAGE Code
    - VAT (EU): EU VAT Number (DE/FR/NL etc prefix)
    - UEN (SG): Singapore Unique Entity Number
    - ABN (AU): Australian Business Number
    - ACN (AU): Australian Company Number
    - TRN (AE): UAE Tax Registration Number
    - Trade License (AE): UAE Trade License
    - IBAN (GLOBAL): International Bank Account Number
    - SWIFT (GLOBAL): SWIFT/BIC Code
    - ISO (GLOBAL): ISO Certification Number
    - Reg No (GLOBAL): Generic Registration Number
    - License No (GLOBAL): Generic License Number
    - Also capture ANY other official registration/tax/company ID numbers

Return ONLY valid JSON array:
[
  {{
    "party_name": "Full legal name",
    "role": "Supplier/Customer/Service Provider/Client/Licensor/Licensee/Bank/etc",
    "address": "address or null",
    "identifiers": [
      {{"type": "GSTIN", "value": "29AAJCN4417K1ZP"}},
      {{"type": "CIN", "value": "U72900KA2016PTC088214"}}
    ]
  }}
]

If no parties found return: []"""


async def extract_party_identifiers(
    full_text: str,
    plan: str = "starter",
    llm=None,
) -> list[dict]:
    """Extract party identifiers using LLM."""
    text_excerpt = full_text[:3000]
    parties_section = _extract_parties_section(full_text)
    if parties_section:
        text_excerpt = parties_section[:3000]

    prompt = PARTY_EXTRACTION_PROMPT.format(text=text_excerpt)

    try:
        import anthropic
        from app.core.config import settings as _s
        client = anthropic.AsyncAnthropic(api_key=_s.ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1000,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.MULTILINE).strip()
        parties = json.loads(raw)

        if not isinstance(parties, list):
            return []

        result = []
        for party in parties:
            if not isinstance(party, dict):
                continue
            name = str(party.get("party_name", "")).strip()
            if not name:
                continue
            identifiers = party.get("identifiers", [])
            if not isinstance(identifiers, list):
                identifiers = []
            result.append({
                "party_name":  name,
                "role":        str(party.get("role", "Party")).strip(),
                "address":     party.get("address"),
                "identifiers": [
                    {"type": str(i.get("type", "")), "value": str(i.get("value", ""))}
                    for i in identifiers
                    if i.get("type") and i.get("value")
                ],
            })

        logger.info("party_identifiers_extracted",
                    parties=len(result),
                    total_ids=sum(len(p["identifiers"]) for p in result))
        return result

    except Exception as e:
        logger.warning("party_extraction_failed", error=str(e))
        return []


def _extract_parties_section(text: str) -> Optional[str]:
    """Extract BETWEEN...AND parties section."""
    patterns = [
        r'(?:BETWEEN|PARTIES)\s*\n(.{100,2000}?)(?:WHEREAS|NOW THEREFORE|ARTICLE 1|1\.\s+DEFINITIONS)',
        r'(?:between|parties)[\s:]*\n(.{100,2000}?)(?:whereas|now therefore|article)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return "PARTIES\n" + m.group(1)
    return None


def build_identifier_summary(parties: list[dict]) -> str:
    """Build searchable text from extracted party identifiers."""
    if not parties:
        return ""
    lines = ["\n=== PARTIES & REGISTRATION IDENTIFIERS ==="]
    for party in parties:
        name = party.get("party_name", "")
        role = party.get("role", "")
        header = f"{name} ({role})" if role else name
        lines.append(f"\n{header}:")
        if party.get("address"):
            lines.append(f"  Address: {party['address']}")
        for id_info in party.get("identifiers", []):
            lines.append(f"  {id_info['type']}: {id_info['value']}")
    return "\n".join(lines)
