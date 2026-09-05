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

    "pharma": {
        "display_name": "Pharmaceutical / Life Sciences",
        "risk_multipliers": {
            "data_protection": 2.0,
            "liability_cap": 2.0,
            "indemnification": 2.0,
            "regulatory_compliance": 2.5,
            "intellectual_property": 2.0,
            "confidentiality": 2.0,
            "warranties": 1.5,
            "insurance": 1.5,
            "audit_rights": 1.5,
            "termination": 1.3,
        },
        "mandatory_clauses": [
            "regulatory_compliance",
            "pharmacovigilance",
            "data_integrity",
            "audit_rights",
            "ip_ownership",
            "confidentiality",
            "insurance",
            "anti_bribery",
            "quality_assurance",
            "change_control",
            "record_retention",
        ],
        "regulatory_frameworks": ["FDA", "EMA", "CDSCO", "GxP", "GCP", "GMP", "ICH", "21 CFR Part 11", "DPDP Act"],
        "red_flags": [
            "No pharmacovigilance or adverse event reporting obligation",
            "IP ownership silent on jointly developed compounds",
            "No data integrity or 21 CFR Part 11 compliance clause",
            "Audit rights exclude regulatory inspector access",
            "No anti-bribery / FCPA clause",
            "Liability cap below 3x annual value for clinical trials",
            "No change control process for GxP-regulated activities",
            "Record retention below regulatory minimum (15-25 years)",
            "Subcontracting of GxP activities without sponsor consent",
            "No qualified person or responsible pharmacist designated",
        ],
        "analysis_guidance": (
            "Pharma/Life Sciences contracts require: pharmacovigilance obligations, "
            "data integrity (21 CFR Part 11, Annex 11), GxP compliance, "
            "regulatory audit access (FDA/EMA/CDSCO inspection rights), "
            "IP ownership for compounds/formulations/data, anti-bribery/FCPA, "
            "change control for regulated processes, record retention (15-25 years), "
            "qualified person responsibilities, and insurance adequacy for clinical trials."
        ),
    },
    "clinical_trials": {
        "display_name": "Clinical Trials / CRO",
        "risk_multipliers": {
            "data_protection": 2.5,
            "liability_cap": 2.5,
            "indemnification": 2.5,
            "regulatory_compliance": 3.0,
            "confidentiality": 2.0,
            "insurance": 2.0,
            "audit_rights": 2.0,
            "termination": 1.5,
        },
        "mandatory_clauses": [
            "subject_safety",
            "informed_consent",
            "adverse_event_reporting",
            "data_ownership",
            "regulatory_compliance",
            "insurance_clinical",
            "indemnification",
            "audit_rights",
            "record_retention",
            "ethics_committee",
            "investigator_obligations",
            "study_termination",
        ],
        "regulatory_frameworks": ["ICH-GCP E6(R2)", "FDA 21 CFR Parts 11/50/56/312", "EMA Clinical Trials Regulation", "CDSCO CT Rules 2019", "Declaration of Helsinki"],
        "red_flags": [
            "No subject safety or adverse event reporting clause",
            "Sponsor indemnification does not cover investigator negligence carve-out",
            "No insurance for clinical trial participants",
            "Data ownership vests in CRO not sponsor",
            "No ethics committee / IRB approval requirement",
            "Study termination clause lacks patient safety trigger",
            "No provision for regulatory inspection cooperation",
            "Record retention below 15 years post-study completion",
            "No protocol deviation reporting mechanism",
            "Missing informed consent process requirements",
        ],
        "analysis_guidance": (
            "Clinical trial agreements are HIGH-RISK by nature due to patient safety. "
            "Mandatory analysis: subject safety provisions, adverse event reporting timelines, "
            "informed consent process, sponsor vs CRO vs investigator responsibilities, "
            "insurance coverage for trial participants, data ownership and access rights, "
            "ethics committee requirements, protocol deviation handling, "
            "study termination triggers (safety vs commercial), "
            "regulatory inspection cooperation, and record retention (15+ years)."
        ),
    },

    "energy_oil_gas": {
        "display_name": "Energy / Oil & Gas",
        "risk_multipliers": {
            "liability_cap": 2.0,
            "indemnification": 2.0,
            "insurance": 2.0,
            "force_majeure": 1.5,
            "regulatory_compliance": 2.0,
            "termination": 1.5,
            "warranties": 1.5,
            "environmental": 2.5,
        },
        "mandatory_clauses": [
            "environmental_compliance",
            "health_safety",
            "insurance",
            "indemnification",
            "decommissioning",
            "regulatory_compliance",
            "force_majeure",
            "change_in_law",
            "liquidated_damages",
            "performance_guarantees",
        ],
        "regulatory_frameworks": ["PNGRB", "MoPNG", "EPA", "OSHA", "ISO 14001", "ISO 45001"],
        "red_flags": [
            "No environmental liability clause",
            "Decommissioning costs not allocated",
            "Insurance below industry minimum",
            "No change-in-law adjustment mechanism",
            "Force majeure excludes regulatory changes",
            "No health and safety obligations",
            "Liquidated damages uncapped",
            "No performance guarantee or bond",
        ],
        "analysis_guidance": (
            "Energy/Oil & Gas contracts require: environmental liability and remediation, "
            "health and safety (HSE) obligations, decommissioning cost allocation, "
            "change-in-law provisions, performance guarantees/bonds, insurance adequacy "
            "(CGL, pollution, well control), force majeure (including sanctions), "
            "and liquidated damages for delay/underperformance."
        ),
    },
    "telecom": {
        "display_name": "Telecommunications",
        "risk_multipliers": {
            "service_levels": 2.0,
            "data_protection": 1.5,
            "regulatory_compliance": 2.0,
            "liability_cap": 1.5,
            "termination": 1.5,
            "business_continuity": 1.5,
            "interconnection": 2.0,
        },
        "mandatory_clauses": [
            "service_levels",
            "network_availability",
            "interconnection",
            "number_portability",
            "data_protection",
            "regulatory_compliance",
            "business_continuity",
            "disaster_recovery",
            "spectrum_rights",
        ],
        "regulatory_frameworks": ["TRAI", "DoT", "ITU", "FCC", "GDPR", "DPDP Act"],
        "red_flags": [
            "SLA below 99.9% for critical infrastructure",
            "No disaster recovery or redundancy clause",
            "Interconnection terms not TRAI-compliant",
            "No number portability provisions",
            "Data retention exceeds regulatory limits",
            "No spectrum sharing/usage restrictions",
        ],
        "analysis_guidance": (
            "Telecom contracts: focus on network SLAs and availability (99.9%+), "
            "interconnection terms, number portability, spectrum rights, "
            "TRAI/DoT regulatory compliance, disaster recovery and redundancy, "
            "data retention and lawful intercept obligations."
        ),
    },
    "government": {
        "display_name": "Government / Public Sector",
        "risk_multipliers": {
            "regulatory_compliance": 2.5,
            "termination": 2.0,
            "audit_rights": 2.0,
            "data_protection": 2.0,
            "liability_cap": 1.5,
            "indemnification": 1.5,
            "transparency": 2.0,
        },
        "mandatory_clauses": [
            "transparency_disclosure",
            "audit_rights",
            "anti_corruption",
            "data_sovereignty",
            "termination_for_convenience",
            "security_clearance",
            "local_content",
            "performance_bank_guarantee",
            "liquidated_damages",
            "dispute_resolution_arbitration",
        ],
        "regulatory_frameworks": ["GFR", "CVC Guidelines", "RTI Act", "GeM", "PPP Policy", "FAR (US)"],
        "red_flags": [
            "No anti-corruption / integrity pact clause",
            "Government termination for convenience without compensation",
            "No data sovereignty / local hosting requirement",
            "Performance bank guarantee below 10% of contract value",
            "No provision for RTI / transparency compliance",
            "Dispute resolution not through arbitration",
            "No local content / Make in India compliance",
            "Liquidated damages exceed 10% of contract value",
        ],
        "analysis_guidance": (
            "Government contracts: focus on termination for convenience (sovereign right), "
            "anti-corruption/integrity pact, audit and CAG access, data sovereignty, "
            "performance bank guarantees, liquidated damages caps, "
            "GeM/procurement compliance, transparency/RTI obligations, "
            "and security clearance requirements."
        ),
    },
    "insurance": {
        "display_name": "Insurance",
        "risk_multipliers": {
            "regulatory_compliance": 2.5,
            "data_protection": 2.0,
            "confidentiality": 2.0,
            "liability_cap": 1.5,
            "audit_rights": 2.0,
            "outsourcing": 2.0,
            "business_continuity": 1.5,
        },
        "mandatory_clauses": [
            "regulatory_compliance",
            "policyholder_data_protection",
            "outsourcing_guidelines",
            "audit_rights",
            "business_continuity",
            "complaints_handling",
            "anti_money_laundering",
            "solvency_reporting",
            "claims_handling",
        ],
        "regulatory_frameworks": ["IRDAI", "Solvency II", "NAIC", "AML/KYC", "DPDP Act"],
        "red_flags": [
            "Outsourcing without IRDAI compliance",
            "No policyholder data protection clause",
            "Claims handling SLA not defined",
            "No anti-money laundering obligations",
            "Business continuity plan not required",
            "Audit rights exclude regulatory access",
        ],
        "analysis_guidance": (
            "Insurance contracts: focus on IRDAI outsourcing guidelines compliance, "
            "policyholder data protection, claims handling SLAs, "
            "anti-money laundering/KYC obligations, solvency reporting, "
            "complaints handling process, and regulatory audit access."
        ),
    },
    "media_entertainment": {
        "display_name": "Media & Entertainment",
        "risk_multipliers": {
            "intellectual_property": 2.5,
            "licensing": 2.0,
            "confidentiality": 1.5,
            "termination": 1.5,
            "indemnification": 1.5,
            "moral_rights": 2.0,
        },
        "mandatory_clauses": [
            "ip_ownership",
            "license_grant",
            "territory_and_term",
            "royalties",
            "moral_rights",
            "content_approval",
            "representations_warranties",
            "indemnification",
            "distribution_rights",
            "sequel_derivative_rights",
        ],
        "regulatory_frameworks": ["Copyright Act", "CBFC", "IT Act", "DMCA", "WIPO"],
        "red_flags": [
            "IP assignment with no reversion clause",
            "Perpetual licence with no termination trigger",
            "No moral rights waiver or retention clause",
            "Territory defined as 'worldwide' without exclusions",
            "Royalty audit rights not specified",
            "No content approval process",
            "Sequel/derivative rights assigned without additional compensation",
        ],
        "analysis_guidance": (
            "Media contracts: focus on IP ownership vs licence, territory and term, "
            "royalty structure and audit rights, moral rights, content approval process, "
            "sequel/derivative/remake rights, distribution platform restrictions, "
            "and reversion of rights on termination."
        ),
    },
    "education": {
        "display_name": "Education / EdTech",
        "risk_multipliers": {
            "data_protection": 2.5,
            "intellectual_property": 1.5,
            "regulatory_compliance": 1.5,
            "accessibility": 2.0,
            "content_licensing": 1.5,
        },
        "mandatory_clauses": [
            "student_data_protection",
            "content_licensing",
            "accessibility_compliance",
            "ip_ownership",
            "service_levels",
            "termination",
            "data_portability",
            "content_accuracy",
        ],
        "regulatory_frameworks": ["FERPA", "COPPA", "NEP 2020", "UGC Guidelines", "AICTE", "DPDP Act"],
        "red_flags": [
            "No student data protection / FERPA compliance",
            "Content licensing allows commercial reuse without consent",
            "No accessibility compliance (WCAG/Section 508)",
            "Student data used for advertising or profiling",
            "No data portability on contract termination",
            "No content accuracy warranty",
        ],
        "analysis_guidance": (
            "Education contracts: focus on student data protection (FERPA/COPPA), "
            "content licensing scope, accessibility compliance (WCAG), "
            "data portability on exit, prohibition on student data monetisation, "
            "content accuracy and update obligations."
        ),
    },
    "construction": {
        "display_name": "Construction / Infrastructure",
        "risk_multipliers": {
            "liability_cap": 2.0,
            "insurance": 2.0,
            "force_majeure": 1.5,
            "termination": 1.5,
            "warranties": 1.5,
            "liquidated_damages": 2.0,
            "health_safety": 2.0,
        },
        "mandatory_clauses": [
            "scope_of_work",
            "payment_milestones",
            "variation_orders",
            "liquidated_damages",
            "defects_liability",
            "retention_money",
            "performance_guarantee",
            "insurance",
            "health_safety",
            "force_majeure",
            "dispute_resolution",
            "completion_certificate",
        ],
        "regulatory_frameworks": ["FIDIC", "RERA", "NBC", "IS Codes", "OSHA", "EHS Standards"],
        "red_flags": [
            "No variation order / change management process",
            "Liquidated damages exceed 10% of contract value",
            "Defects liability period below 12 months",
            "No retention money clause",
            "Performance guarantee below 5% of contract value",
            "No health and safety obligations",
            "Payment not linked to milestones or completion certificates",
            "No provision for extension of time (EOT)",
        ],
        "analysis_guidance": (
            "Construction contracts: focus on FIDIC compliance, payment milestones "
            "and retention, variation/change order process, liquidated damages cap, "
            "defects liability period, performance bank guarantee, "
            "health and safety obligations, extension of time provisions, "
            "and insurance (CAR, third-party, workmen's compensation)."
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
