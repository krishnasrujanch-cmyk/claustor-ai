"""
Industry Playbooks
==================
Risk weights and compliance requirements per industry.
Loaded during pipeline to adjust risk scoring.
"""

INDUSTRY_PLAYBOOKS = {
    "financial_services": {
        "display_name": "Financial Services / Banking",
        "risk_multipliers": {
            "data_protection": 2.0,
            "liability_cap": 1.5,
            "indemnification": 1.5,
            "regulatory_compliance": 2.0,
            "audit_rights": 1.5,
            "confidentiality": 1.5,
            "termination": 1.2,
            "subcontracting": 1.5,
            "insurance": 1.3,
        },
        "mandatory_clauses": [
            "data_protection",
            "audit_rights",
            "regulatory_compliance",
            "business_continuity",
            "subcontracting_consent",
            "data_residency",
            "breach_notification",
        ],
        "regulatory_frameworks": ["RBI Guidelines", "DPDP Act", "SEBI", "PCI-DSS"],
        "red_flags": [
            "No data residency clause in a cross-border contract",
            "Subcontracting without prior written consent",
            "Liability cap below 2x annual contract value",
            "No breach notification timeline specified",
            "No audit rights for regulator access",
            "Data processing without DPDP compliance",
        ],
        "analysis_guidance": (
            "Banking/financial contracts require heightened scrutiny on: "
            "data residency and cross-border transfers, regulatory audit access, "
            "outsourcing guidelines (RBI), breach notification timelines, "
            "business continuity and disaster recovery obligations, and "
            "subcontractor oversight requirements."
        ),
    },
    "healthcare": {
        "display_name": "Healthcare / Pharma",
        "risk_multipliers": {
            "data_protection": 2.5,
            "confidentiality": 2.0,
            "liability_cap": 1.5,
            "indemnification": 1.5,
            "insurance": 1.5,
            "regulatory_compliance": 2.0,
            "warranties": 1.3,
        },
        "mandatory_clauses": [
            "data_protection",
            "patient_data_handling",
            "regulatory_compliance",
            "insurance",
            "audit_rights",
            "quality_standards",
        ],
        "regulatory_frameworks": ["HIPAA", "DPDP Act", "FDA", "GxP"],
        "red_flags": [
            "No patient data protection clause",
            "Liability cap below industry standard",
            "No quality assurance obligations",
            "Missing regulatory compliance warranty",
        ],
        "analysis_guidance": (
            "Healthcare contracts need focus on: patient data handling, "
            "HIPAA/regulatory compliance, quality standards (GxP), "
            "insurance adequacy, pharmacovigilance obligations."
        ),
    },
    "it_saas": {
        "display_name": "IT / SaaS / Technology",
        "risk_multipliers": {
            "intellectual_property": 2.0,
            "data_protection": 1.5,
            "service_levels": 1.5,
            "liability_cap": 1.3,
            "indemnification": 1.3,
            "termination": 1.2,
        },
        "mandatory_clauses": [
            "ip_ownership",
            "service_levels",
            "data_protection",
            "escrow",
            "business_continuity",
        ],
        "regulatory_frameworks": ["SOC 2", "ISO 27001", "GDPR", "DPDP Act"],
        "red_flags": [
            "IP ownership silent on custom deliverables",
            "No source code escrow for critical systems",
            "SLA credits as sole remedy with no termination trigger",
            "No data portability/exit clause",
            "Vendor retains rights to use customer data for training",
        ],
        "analysis_guidance": (
            "IT/SaaS contracts: focus on IP ownership (especially custom work), "
            "SLA structure and remedies, data portability on exit, "
            "vendor lock-in risks, security certifications, and "
            "whether service credits are sole remedy."
        ),
    },
    "manufacturing": {
        "display_name": "Manufacturing / Supply Chain",
        "risk_multipliers": {
            "delivery": 1.5,
            "warranties": 1.5,
            "liability_cap": 1.3,
            "quality_standards": 1.5,
            "force_majeure": 1.3,
            "insurance": 1.3,
        },
        "mandatory_clauses": [
            "delivery_terms",
            "quality_standards",
            "inspection_rights",
            "warranties",
            "force_majeure",
            "insurance",
        ],
        "regulatory_frameworks": ["ISO 9001", "Industry Safety Standards"],
        "red_flags": [
            "No liquidated damages for late delivery",
            "Warranty period below industry standard",
            "Force majeure too broadly defined",
            "No right to inspect before acceptance",
        ],
        "analysis_guidance": (
            "Manufacturing contracts: focus on delivery terms (Incoterms), "
            "quality standards and inspection rights, warranty scope, "
            "price escalation mechanisms, minimum order commitments."
        ),
    },
    "real_estate": {
        "display_name": "Real Estate / Property",
        "risk_multipliers": {
            "term": 1.3,
            "payment_terms": 1.5,
            "termination": 1.5,
            "insurance": 1.3,
            "maintenance": 1.3,
        },
        "mandatory_clauses": [
            "premises_description",
            "rent_and_escalation",
            "security_deposit",
            "maintenance",
            "insurance",
            "termination",
        ],
        "regulatory_frameworks": ["RERA", "Local Tenancy Laws"],
        "red_flags": [
            "Escalation above market rate",
            "No early termination clause",
            "Broad restoration obligation",
            "Security deposit above legal limit",
        ],
        "analysis_guidance": (
            "Real estate contracts: focus on rent escalation, lock-in period, "
            "maintenance responsibilities, RERA compliance, security deposit terms."
        ),
    },
    "general": {
        "display_name": "General",
        "risk_multipliers": {},
        "mandatory_clauses": [],
        "regulatory_frameworks": [],
        "red_flags": [],
        "analysis_guidance": "Apply standard contract analysis best practices.",
    },
}


def get_playbook(industry: str) -> dict:
    """Get playbook for an industry. Falls back to 'general'."""
    ind = (industry or "general").strip().lower()
    if ind in INDUSTRY_PLAYBOOKS:
        return INDUSTRY_PLAYBOOKS[ind]
    # Fuzzy match
    for key, pb in INDUSTRY_PLAYBOOKS.items():
        if ind in key or key in ind:
            return pb
    return INDUSTRY_PLAYBOOKS["general"]


def apply_industry_weight(base_score: float, clause_type: str, industry: str) -> float:
    """Apply industry risk multiplier to a clause's base score."""
    playbook = get_playbook(industry)
    multiplier = playbook["risk_multipliers"].get(clause_type, 1.0)
    return min(100.0, base_score * multiplier)
