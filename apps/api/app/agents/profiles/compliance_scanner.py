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
        # General industry with no specific regulation — run DPDP only (Indian default)
        if industry == "general":
            checklists = [{"code": "dpdp_act", **COMPLIANCE_CHECKLISTS["dpdp_act"]}]
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
    """Check if a required clause is present in the text."""
    matched = []
    for keyword in clause["keywords"]:
        # Support regex patterns
        if ".*" in keyword:
            if re.search(keyword, text, re.IGNORECASE):
                matched.append(keyword)
        elif keyword.lower() in text:
            matched.append(keyword)
    return matched


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
