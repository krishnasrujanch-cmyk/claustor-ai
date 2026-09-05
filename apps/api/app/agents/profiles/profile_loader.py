"""
Profile Loader
==============
Loads and combines contract type + industry + role profiles
into a single analysis context for the LLM.
"""
from app.agents.profiles.contract_types import get_profile, get_missing_clauses
from app.agents.profiles.industry_playbooks import get_playbook
from app.agents.profiles.role_perspective import get_perspective


def build_analysis_context(
    contract_type: str,
    industry: str = "general",
    role: str = "neutral",
    found_clauses: list[str] | None = None,
) -> str:
    """
    Build a combined analysis context string for the LLM.
    Used in both pipeline extraction and chat answering.
    """
    profile = get_profile(contract_type)
    playbook = get_playbook(industry)
    perspective = get_perspective(role)

    sections = []

    # Contract type context
    sections.append(f"CONTRACT TYPE: {profile['full_name']}")
    sections.append(f"EXTRACTION FOCUS: {profile['extraction_guidance']}")
    
    # Expected clauses
    if profile["expected_clauses"]:
        expected = ", ".join(profile["expected_clauses"][:15])
        sections.append(f"EXPECTED CLAUSES: {expected}")

    # Missing clauses
    if found_clauses:
        missing = get_missing_clauses(contract_type, found_clauses)
        if missing:
            sections.append(f"MISSING CLAUSES (flag these): {', '.join(missing[:10])}")

    # Industry context
    if playbook.get("analysis_guidance") and industry != "general":
        sections.append(f"INDUSTRY ({playbook['display_name']}): {playbook['analysis_guidance']}")
        if playbook.get("red_flags"):
            flags = "; ".join(playbook["red_flags"][:5])
            sections.append(f"INDUSTRY RED FLAGS: {flags}")
        if playbook.get("regulatory_frameworks"):
            sections.append(f"REGULATORY: {', '.join(playbook['regulatory_frameworks'])}")

    # High-risk patterns to watch
    if profile.get("high_risk_patterns"):
        patterns = ", ".join(p.replace("_", " ") for p in profile["high_risk_patterns"][:7])
        sections.append(f"HIGH-RISK PATTERNS: {patterns}")

    # Role perspective
    sections.append(f"ANALYSIS PERSPECTIVE: {perspective['analysis_instruction']}")

    return "\n".join(sections)
