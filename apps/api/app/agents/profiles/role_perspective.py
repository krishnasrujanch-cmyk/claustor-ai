"""
Party Role Perspective
======================
Adjusts risk analysis based on which party the user represents.
"""

ROLE_PERSPECTIVES = {
    "customer": {
        "risk_focus": [
            "Liability caps that are too LOW (favour vendor)",
            "Termination rights that are ASYMMETRIC (vendor can exit, customer cannot)",
            "Auto-renewal with short notice period (lock-in risk)",
            "Indemnification obligations that are ONE-SIDED (customer indemnifies more)",
            "Service credits as SOLE REMEDY (no termination trigger for poor performance)",
            "Retroactive billing or true-up mechanisms",
            "Deemed acceptance with SHORT windows",
            "Broad force majeure favouring vendor",
            "IP ownership vesting in vendor for custom work",
            "Data portability restrictions on exit",
        ],
        "analysis_instruction": (
            "Analyse this contract FROM THE CUSTOMER'S PERSPECTIVE. "
            "Flag clauses that favour the vendor disproportionately. "
            "Highlight lock-in risks, cost escalation mechanisms, "
            "and weak remedies for poor performance."
        ),
    },
    "vendor": {
        "risk_focus": [
            "Liability caps that are UNCAPPED or too HIGH",
            "Broad indemnification obligations on vendor",
            "Stringent SLAs with penalties that exceed margin",
            "Unlimited data breach liability",
            "Onerous audit rights allowing fishing expeditions",
            "Termination for convenience with short notice",
            "Scope creep through vague change management",
            "Payment terms that are too long (cashflow risk)",
            "Broad IP assignment without fair compensation",
        ],
        "analysis_instruction": (
            "Analyse this contract FROM THE VENDOR'S PERSPECTIVE. "
            "Flag clauses that expose the vendor to disproportionate risk. "
            "Highlight uncapped liabilities, onerous SLAs, "
            "and cashflow risks from payment terms."
        ),
    },
    "neutral": {
        "risk_focus": [
            "Any asymmetric provisions favouring one party",
            "Uncapped or unusually capped liabilities",
            "Retroactive or automatic mechanisms",
            "Missing standard clauses for this contract type",
        ],
        "analysis_instruction": (
            "Analyse this contract NEUTRALLY. "
            "Flag asymmetric provisions and unusual terms "
            "regardless of which party they favour."
        ),
    },
}


def get_perspective(role: str = "neutral") -> dict:
    """Get analysis perspective for a party role."""
    return ROLE_PERSPECTIVES.get(role, ROLE_PERSPECTIVES["neutral"])
