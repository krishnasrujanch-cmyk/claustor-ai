"""
Claustor AI — Compliance Scanner
Scans contract text against regulatory checklists.
Produces a compliance score and gap analysis.
"""
import re
import structlog
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.profiles.compliance_checklists import (
    get_applicable_checklists,
    get_checklist,
    COMPLIANCE_CHECKLISTS,
)

logger = structlog.get_logger(__name__)


async def scan_contract_compliance(
    db: AsyncSession,
    contract_id: UUID,
    industry: str = "general",
    regulations: list[str] | None = None,
) -> dict:
    """
    Scan a contract against applicable compliance checklists.
    Returns compliance scores and gap analysis.
    """
    # Load contract chunks
    r = await db.execute(text("""
        SELECT text FROM contract_chunks
        WHERE contract_id = :cid AND is_parent = false
        ORDER BY chunk_index
    """), {"cid": str(contract_id)})
    chunks = r.fetchall()
    if not chunks:
        return {"error": "No contract text found"}

    full_text = "\n".join(row[0] for row in chunks).lower()

    # Determine which checklists to run
    if regulations:
        checklists = [{"code": r, **COMPLIANCE_CHECKLISTS[r]} 
                      for r in regulations if r in COMPLIANCE_CHECKLISTS]
    else:
        checklists = get_applicable_checklists(industry)

    if not checklists:
        if industry == "general":
            # Check if contract involves personal data before applying DPDP
            if _involves_personal_data(full_text):
                checklists = [{"code": "dpdp_act", **COMPLIANCE_CHECKLISTS["dpdp_act"]}]
            else:
                return {
                    "contract_id": str(contract_id),
                    "industry": industry,
                    "overall_score": None,
                    "total_required": 0,
                    "total_found": 0,
                    "total_missing": 0,
                    "regulations": [],
                    "note": "No data protection regulations applicable — contract does not involve personal data processing.",
                }
        else:
            return {"error": f"No compliance checklists for industry: {industry}"}

    results = []
    for checklist in checklists:
        result = _scan_against_checklist(full_text, checklist)
        results.append(result)

    # Overall score
    total_required = sum(r["total_clauses"] for r in results)
    total_found = sum(r["found_count"] for r in results)
    overall_score = round(total_found / total_required * 100, 1) if total_required > 0 else 0

    return {
        "contract_id": str(contract_id),
        "industry": industry,
        "overall_score": overall_score,
        "total_required": total_required,
        "total_found": total_found,
        "total_missing": total_required - total_found,
        "regulations": results,
    }


def _involves_personal_data(text: str) -> bool:
    """Detect if contract involves personal data processing."""
    data_indicators = [
        "personal data", "personal information", "data subject",
        "data processing", "data controller", "data processor",
        "privacy", "PII", "sensitive data", "customer data",
        "user data", "employee data", "health data", "biometric",
        "data protection", "GDPR", "DPDP", "consent.*data",
        "information.*process", "collect.*data", "store.*data",
    ]
    matches = sum(1 for kw in data_indicators if kw.lower() in text)
    return matches >= 2  # need at least 2 indicators


def _scan_against_checklist(text: str, checklist: dict) -> dict:
    """Scan text against a single compliance checklist."""
    code = checklist["code"]
    display_name = checklist["display_name"]
    required = checklist["required_clauses"]

    found = []
    missing = []

    for clause in required:
        matched = _check_clause_presence(text, clause)
        if matched:
            found.append({
                "id": clause["id"],
                "title": clause["title"],
                "severity": clause["severity"],
                "status": "found",
                "matched_keywords": matched,
            })
        else:
            missing.append({
                "id": clause["id"],
                "title": clause["title"],
                "description": clause["description"],
                "severity": clause["severity"],
                "status": "missing",
            })

    total = len(required)
    score = round(len(found) / total * 100, 1) if total > 0 else 0

    # Count critical missing
    critical_missing = [m for m in missing if m["severity"] == "critical"]

    return {
        "regulation": code,
        "display_name": display_name,
        "score": score,
        "total_clauses": total,
        "found_count": len(found),
        "missing_count": len(missing),
        "critical_missing": len(critical_missing),
        "found": found,
        "missing": missing,
        "risk_level": _score_to_risk(score, len(critical_missing)),
    }


def _check_clause_presence(text: str, clause: dict) -> list[str]:
    """Check if a required clause is present in the text.
    Uses keyword matching + word stem expansion for broader coverage.
    """
    matched = []
    for keyword in clause["keywords"]:
        # Support regex patterns
        if ".*" in keyword:
            if re.search(keyword, text, re.IGNORECASE):
                matched.append(keyword)
        elif keyword.lower() in text:
            matched.append(keyword)

    # If no direct match, try stem-expanded matching
    if not matched:
        expanded = _expand_keywords(clause["keywords"])
        for kw in expanded:
            if kw in text:
                matched.append(kw)

    return matched


# Common word stems and synonyms for legal/compliance terms
_SYNONYM_MAP = {
    "deletion": ["destroy", "erase", "purge", "remove", "wipe", "disposal"],
    "security": ["cybersecurity", "information security", "infosec", "security policy",
                 "security standard", "security control", "security protocol", "protective measure"],
    "consent": ["permission", "authorisation", "authorization", "approval", "agreement to process"],
    "retention": ["storage period", "keep.*data", "preserve.*data", "maintain.*record"],
    "breach": ["incident", "unauthorized access", "security event", "compromise"],
    "confidential": ["non-disclosure", "proprietary", "trade secret", "restricted information"],
    "audit": ["inspection", "examination", "review right", "right to examine", "access to records"],
    "transfer": ["transmit", "share.*data", "disclose.*data", "send.*data", "move.*data"],
    "grievance": ["complaint", "dispute.*data", "remedy", "recourse", "redress"],
    "processing": ["handling", "use of data", "data usage", "data handling", "data operation"],
    "safeguard": ["protective measure", "security control", "technical measure", "organizational measure"],
    "residency": ["localization", "stored in india", "data.*india", "within india", "local storage"],
    "continuity": ["disaster recovery", "backup", "resilience", "failover", "recovery plan"],
    "subcontract": ["sub-contract", "further outsourc", "third party engag", "delegate.*service"],
    "termination": ["expiry", "end of agreement", "cessation", "wind-down", "conclusion of"],
    "monitor": ["oversight", "supervision", "review.*performance", "track.*compliance"],
}


def _expand_keywords(keywords: list[str]) -> list[str]:
    """Expand keywords with synonyms for broader matching."""
    expanded = set()
    for kw in keywords:
        kw_lower = kw.lower()
        for stem, synonyms in _SYNONYM_MAP.items():
            if stem in kw_lower:
                expanded.update(s.lower() for s in synonyms)
    return list(expanded)


def _score_to_risk(score: float, critical_missing: int) -> str:
    """Convert compliance score to risk level."""
    if critical_missing >= 3:
        return "critical"
    if score >= 80 and critical_missing == 0:
        return "low"
    if score >= 60:
        return "medium"
    return "high"


def format_compliance_report(result: dict) -> str:
    """Format compliance scan results as readable text."""
    lines = []
    lines.append(f"# Compliance Analysis")
    lines.append(f"**Overall Score: {result['overall_score']}%** "
                 f"({result['total_found']}/{result['total_required']} requirements met)\n")

    for reg in result["regulations"]:
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🚨"}.get(reg["risk_level"], "⚪")
        lines.append(f"## {reg['display_name']}")
        lines.append(f"Score: **{reg['score']}%** | Risk: {risk_emoji} {reg['risk_level'].upper()}")
        lines.append(f"Found: {reg['found_count']}/{reg['total_clauses']} | "
                     f"Critical gaps: {reg['critical_missing']}\n")

        if reg["missing"]:
            lines.append("### Missing Requirements")
            for m in reg["missing"]:
                severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(m["severity"], "⚪")
                lines.append(f"- {severity_icon} **{m['title']}** [{m['severity'].upper()}]")
                lines.append(f"  {m['description']}")

        if reg["found"]:
            lines.append("\n### Requirements Met")
            for f in reg["found"]:
                lines.append(f"- ✅ {f['title']}")

        lines.append("")

    return "\n".join(lines)
