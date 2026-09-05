"""
Contract Type Profiles
======================
Defines expected clauses, risk patterns, and extraction guidance
per contract type. Used by the pipeline to guide LLM extraction.
"""

CONTRACT_TYPE_PROFILES = {
    "MSA": {
        "full_name": "Master Services Agreement",
        "expected_clauses": [
            "term_and_renewal",
            "termination_for_convenience",
            "termination_for_cause",
            "liability_cap",
            "consequential_damages",
            "indemnification",
            "payment_terms",
            "invoicing_and_billing",
            "service_levels",
            "service_credits",
            "intellectual_property",
            "data_protection",
            "confidentiality",
            "insurance",
            "force_majeure",
            "governing_law",
            "dispute_resolution",
            "change_management",
            "audit_rights",
            "subcontracting",
        ],
        "high_risk_patterns": [
            "asymmetric_termination",
            "uncapped_liability",
            "retroactive_billing",
            "auto_renewal_without_notice",
            "deemed_acceptance",
            "unilateral_amendment",
            "broad_indemnification",
        ],
        "extraction_guidance": (
            "Pay special attention to: liability cap structure (direct vs consequential, "
            "per-SOW vs aggregate), termination rights per party (convenience vs cause, "
            "notice periods per term phase), billing mechanisms (true-up, retroactive, "
            "committed spend), service credit caps, and IP ownership per SOW."
        ),
    },
    "NDA": {
        "full_name": "Non-Disclosure Agreement",
        "expected_clauses": [
            "definition_of_confidential_info",
            "exclusions",
            "permitted_disclosure",
            "term_and_survival",
            "return_of_materials",
            "remedies",
            "governing_law",
            "non_solicitation",
        ],
        "high_risk_patterns": [
            "overbroad_definition",
            "no_expiry",
            "unilateral_obligations",
            "residuals_clause",
            "no_return_obligation",
        ],
        "extraction_guidance": (
            "Focus on: scope of confidential information definition, carve-outs, "
            "survival period after termination, whether obligations are mutual or "
            "one-sided, residuals clause, and remedies (injunctive relief)."
        ),
    },
    "SLA": {
        "full_name": "Service Level Agreement",
        "expected_clauses": [
            "service_definitions",
            "performance_metrics",
            "measurement_methodology",
            "service_credits",
            "credit_cap",
            "exclusions",
            "reporting",
            "remediation",
            "escalation",
            "termination_trigger",
        ],
        "high_risk_patterns": [
            "credit_cap_too_low",
            "sole_remedy_clause",
            "vendor_controlled_measurement",
            "broad_exclusions",
            "no_termination_trigger",
        ],
        "extraction_guidance": (
            "Focus on: uptime/availability targets, measurement methodology "
            "(who measures, what tools), service credit calculation and cap, "
            "whether credits are sole remedy, exclusion windows, and whether "
            "persistent SLA failures trigger termination rights."
        ),
    },
    "Employment": {
        "full_name": "Employment Agreement",
        "expected_clauses": [
            "compensation",
            "benefits",
            "term_and_probation",
            "termination",
            "notice_period",
            "non_compete",
            "non_solicitation",
            "confidentiality",
            "intellectual_property",
            "severance",
            "governing_law",
        ],
        "high_risk_patterns": [
            "broad_non_compete",
            "ip_assignment_overreach",
            "unilateral_termination",
            "clawback_provisions",
            "garden_leave",
        ],
        "extraction_guidance": (
            "Focus on: compensation structure (fixed + variable), non-compete "
            "scope and duration, IP assignment breadth, notice periods per party, "
            "severance triggers and amounts, probation terms."
        ),
    },
    "Vendor": {
        "full_name": "Vendor/Supplier Agreement",
        "expected_clauses": [
            "scope_of_supply",
            "pricing",
            "payment_terms",
            "delivery_terms",
            "warranties",
            "liability",
            "indemnification",
            "termination",
            "force_majeure",
            "quality_standards",
            "inspection_rights",
            "insurance",
        ],
        "high_risk_patterns": [
            "price_escalation_uncapped",
            "warranty_disclaimer",
            "liability_exclusions",
            "sole_source_dependency",
            "minimum_purchase_commitment",
        ],
        "extraction_guidance": (
            "Focus on: pricing mechanism (fixed vs variable, escalation), "
            "delivery terms (Incoterms, penalties), warranty scope and exclusions, "
            "liability cap, minimum purchase commitments, quality acceptance criteria."
        ),
    },
    "License": {
        "full_name": "License Agreement",
        "expected_clauses": [
            "grant_of_license",
            "scope_and_restrictions",
            "fees_and_royalties",
            "term_and_renewal",
            "ip_ownership",
            "warranties",
            "indemnification",
            "termination",
            "post_termination",
            "audit_rights",
        ],
        "high_risk_patterns": [
            "scope_creep",
            "audit_with_retroactive_billing",
            "auto_renewal_price_increase",
            "termination_kills_perpetual",
            "sublicense_restrictions",
        ],
        "extraction_guidance": (
            "Focus on: license scope (perpetual vs term, territory, users), "
            "fee structure (one-time vs recurring, royalties, true-up), "
            "audit rights and consequences, post-termination rights, "
            "sublicensing restrictions."
        ),
    },
    "Lease": {
        "full_name": "Lease/Rental Agreement",
        "expected_clauses": [
            "premises",
            "term",
            "rent_and_escalation",
            "security_deposit",
            "maintenance",
            "alterations",
            "insurance",
            "termination",
            "renewal",
            "governing_law",
        ],
        "high_risk_patterns": [
            "uncapped_escalation",
            "no_early_termination",
            "broad_restoration_obligation",
            "one_sided_renewal",
        ],
        "extraction_guidance": (
            "Focus on: rent amount and escalation mechanism, lock-in period, "
            "early termination penalties, security deposit terms, "
            "maintenance responsibilities, renewal terms."
        ),
    },
    "Loan": {
        "full_name": "Loan/Credit Agreement",
        "expected_clauses": [
            "principal_and_interest",
            "repayment_schedule",
            "prepayment",
            "security_collateral",
            "covenants",
            "events_of_default",
            "remedies",
            "representations",
            "governing_law",
        ],
        "high_risk_patterns": [
            "cross_default",
            "material_adverse_change",
            "prepayment_penalty",
            "broad_covenants",
            "acceleration_triggers",
        ],
        "extraction_guidance": (
            "Focus on: interest rate (fixed/variable, benchmark), repayment "
            "schedule, prepayment rights and penalties, covenants (financial "
            "and operational), events of default, cross-default provisions."
        ),
    },
    "Other": {
        "full_name": "General Contract",
        "expected_clauses": [
            "term",
            "termination",
            "liability",
            "payment",
            "confidentiality",
            "governing_law",
        ],
        "high_risk_patterns": [
            "asymmetric_terms",
            "uncapped_liability",
            "auto_renewal",
        ],
        "extraction_guidance": (
            "Extract all material clauses with focus on: financial obligations, "
            "liability and indemnity, termination rights, and any unusual provisions."
        ),
    },
}


def get_profile(contract_type: str) -> dict:
    """Get profile for a contract type. Falls back to 'Other'."""
    ct = (contract_type or "Other").strip()
    # Try exact match
    if ct in CONTRACT_TYPE_PROFILES:
        return CONTRACT_TYPE_PROFILES[ct]
    # Try case-insensitive
    for key, profile in CONTRACT_TYPE_PROFILES.items():
        if key.lower() == ct.lower() or profile["full_name"].lower() == ct.lower():
            return profile
    return CONTRACT_TYPE_PROFILES["Other"]


def get_missing_clauses(contract_type: str, found_clauses: list[str]) -> list[str]:
    """Return expected clauses not found in the contract."""
    profile = get_profile(contract_type)
    expected = set(profile["expected_clauses"])
    found = set(c.lower().replace(" ", "_") for c in found_clauses)
    return sorted(expected - found)
