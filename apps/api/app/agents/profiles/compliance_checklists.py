"""
Claustor AI — Regulatory Compliance Checklists
Required clauses per regulation for contract compliance scoring.
"""

COMPLIANCE_CHECKLISTS = {
    "dpdp_act": {
        "display_name": "Digital Personal Data Protection Act, 2023 (DPDP)",
        "jurisdiction": "India",
        "applies_to": ["financial_services", "healthcare", "pharma", "it_saas", "telecom", "insurance", "retail", "manufacturing", "energy_oil_gas"],
        "required_clauses": [
            {
                "id": "dpdp_01",
                "title": "Purpose of Data Processing",
                "description": "Contract must specify the purpose for which personal data is being processed",
                "keywords": ["purpose of processing", "data processing purpose", "purpose limitation", "specified purpose", "lawful purpose"],
                "severity": "critical",
            },
            {
                "id": "dpdp_02",
                "title": "Consent Mechanism",
                "description": "Clear consent mechanism for data collection and processing must be defined",
                "keywords": ["consent", "data subject consent", "informed consent", "opt-in", "consent withdrawal"],
                "severity": "critical",
            },
            {
                "id": "dpdp_03",
                "title": "Data Retention Period",
                "description": "Maximum data retention period must be specified",
                "keywords": ["data retention", "retention period", "data storage duration", "retain personal data", "storage limitation"],
                "severity": "high",
            },
            {
                "id": "dpdp_04",
                "title": "Data Deletion on Termination",
                "description": "Obligation to delete or return personal data upon contract termination",
                "keywords": ["data deletion", "data destruction", "return of data", "delete personal data", "data erasure", "secure deletion"],
                "severity": "critical",
            },
            {
                "id": "dpdp_05",
                "title": "Breach Notification Timeline",
                "description": "Timeline for notifying data breaches (recommended 72 hours)",
                "keywords": ["breach notification", "data breach", "security incident", "notify.*breach", "incident notification", "72 hours"],
                "severity": "critical",
            },
            {
                "id": "dpdp_06",
                "title": "Data Protection Officer",
                "description": "Appointment of Data Protection Officer or equivalent",
                "keywords": ["data protection officer", "DPO", "privacy officer", "data privacy lead"],
                "severity": "high",
            },
            {
                "id": "dpdp_07",
                "title": "Cross-Border Transfer Restrictions",
                "description": "Restrictions on transferring personal data outside India",
                "keywords": ["cross-border", "data transfer", "data localization", "data residency", "transfer outside India", "offshore"],
                "severity": "critical",
            },
            {
                "id": "dpdp_08",
                "title": "Grievance Redressal",
                "description": "Mechanism for data subjects to raise grievances",
                "keywords": ["grievance", "complaint", "data subject rights", "redressal", "remedy"],
                "severity": "medium",
            },
            {
                "id": "dpdp_09",
                "title": "Data Security Measures",
                "description": "Reasonable security safeguards for personal data",
                "keywords": ["security safeguard", "encryption", "access control", "security measure", "data security", "reasonable security"],
                "severity": "high",
            },
            {
                "id": "dpdp_10",
                "title": "Sub-processor Restrictions",
                "description": "Restrictions on engaging sub-processors for data processing",
                "keywords": ["sub-processor", "subcontract", "third party process", "onward transfer", "sub-contract"],
                "severity": "high",
            },
        ],
    },
    "rbi_outsourcing": {
        "display_name": "RBI Outsourcing Guidelines",
        "jurisdiction": "India",
        "applies_to": ["financial_services", "insurance"],
        "required_clauses": [
            {
                "id": "rbi_01",
                "title": "Prior Approval for Material Outsourcing",
                "description": "Board-level approval required for material outsourcing arrangements",
                "keywords": ["board approval", "material outsourcing", "prior approval", "governing body"],
                "severity": "critical",
            },
            {
                "id": "rbi_02",
                "title": "Subcontracting with Consent",
                "description": "Service provider cannot subcontract without prior written consent",
                "keywords": ["subcontract", "sub-contract", "prior written consent", "subcontracting", "further outsourcing"],
                "severity": "critical",
            },
            {
                "id": "rbi_03",
                "title": "Regulator Audit Rights",
                "description": "RBI and its agents must have right to audit the service provider",
                "keywords": ["regulator.*audit", "RBI.*access", "regulatory audit", "inspection right", "regulator.*inspect"],
                "severity": "critical",
            },
            {
                "id": "rbi_04",
                "title": "Business Continuity Plan",
                "description": "Service provider must maintain a business continuity and disaster recovery plan",
                "keywords": ["business continuity", "disaster recovery", "BCP", "DR plan", "continuity plan"],
                "severity": "critical",
            },
            {
                "id": "rbi_05",
                "title": "Data Residency in India",
                "description": "Customer data must be stored within India",
                "keywords": ["data residency", "data localization", "stored in India", "data.*India", "within India"],
                "severity": "critical",
            },
            {
                "id": "rbi_06",
                "title": "Exit Management Plan",
                "description": "Clear exit strategy and transition plan on contract termination",
                "keywords": ["exit management", "exit plan", "transition plan", "wind-down", "transition assistance", "exit strategy"],
                "severity": "high",
            },
            {
                "id": "rbi_07",
                "title": "Concentration Risk",
                "description": "Assessment of concentration risk from single vendor dependency",
                "keywords": ["concentration risk", "vendor dependency", "single point", "alternative provider"],
                "severity": "medium",
            },
            {
                "id": "rbi_08",
                "title": "Confidentiality Obligations",
                "description": "Strong confidentiality and non-disclosure obligations on service provider",
                "keywords": ["confidential", "non-disclosure", "NDA", "secrecy", "proprietary information"],
                "severity": "high",
            },
            {
                "id": "rbi_09",
                "title": "Performance Monitoring",
                "description": "Right to monitor service provider performance and SLA compliance",
                "keywords": ["performance monitor", "SLA", "service level", "KPI", "performance review"],
                "severity": "high",
            },
            {
                "id": "rbi_10",
                "title": "Termination Rights",
                "description": "Clear termination rights including for regulatory non-compliance",
                "keywords": ["terminat", "right to terminate", "termination for cause", "regulatory.*terminat"],
                "severity": "high",
            },
        ],
    },
    "sebi_outsourcing": {
        "display_name": "SEBI Outsourcing Guidelines",
        "jurisdiction": "India",
        "applies_to": ["financial_services"],
        "required_clauses": [
            {
                "id": "sebi_01",
                "title": "KYC Compliance",
                "description": "Service provider must comply with KYC/AML requirements",
                "keywords": ["KYC", "know your customer", "anti-money laundering", "AML", "customer due diligence"],
                "severity": "critical",
            },
            {
                "id": "sebi_02",
                "title": "Data Localization",
                "description": "Trading data and investor data must be stored in India",
                "keywords": ["data localization", "data residency", "stored in India", "Indian jurisdiction"],
                "severity": "critical",
            },
            {
                "id": "sebi_03",
                "title": "Audit Trail",
                "description": "Complete audit trail for all transactions and activities",
                "keywords": ["audit trail", "transaction log", "activity log", "audit record", "traceability"],
                "severity": "high",
            },
            {
                "id": "sebi_04",
                "title": "Risk Management Framework",
                "description": "Outsourcing risk management framework and assessment",
                "keywords": ["risk management", "risk assessment", "risk framework", "operational risk"],
                "severity": "high",
            },
            {
                "id": "sebi_05",
                "title": "Regulatory Reporting",
                "description": "Obligation to support regulatory reporting requirements",
                "keywords": ["regulatory report", "SEBI report", "compliance report", "statutory report"],
                "severity": "high",
            },
            {
                "id": "sebi_06",
                "title": "Investor Data Protection",
                "description": "Protection of investor and client sensitive data",
                "keywords": ["investor data", "client data", "sensitive data", "data protection", "information security"],
                "severity": "critical",
            },
        ],
    },
    "gdpr": {
        "display_name": "General Data Protection Regulation (GDPR)",
        "jurisdiction": "EU",
        "applies_to": ["financial_services", "healthcare", "pharma", "it_saas", "telecom", "insurance", "retail", "media_entertainment", "manufacturing"],
        "required_clauses": [
            {
                "id": "gdpr_01",
                "title": "Lawful Basis for Processing",
                "description": "Specified lawful basis for processing personal data",
                "keywords": ["lawful basis", "legal basis", "legitimate interest", "contractual necessity", "consent"],
                "severity": "critical",
            },
            {
                "id": "gdpr_02",
                "title": "Data Subject Rights",
                "description": "Support for data subject rights (access, rectification, erasure, portability)",
                "keywords": ["data subject right", "right of access", "right to erasure", "data portability", "right to rectification"],
                "severity": "critical",
            },
            {
                "id": "gdpr_03",
                "title": "Data Processing Agreement",
                "description": "Formal data processing agreement with processor obligations",
                "keywords": ["data processing agreement", "DPA", "processor agreement", "data processor"],
                "severity": "critical",
            },
            {
                "id": "gdpr_04",
                "title": "International Data Transfer",
                "description": "Adequate safeguards for international data transfers (SCCs, adequacy)",
                "keywords": ["standard contractual clause", "SCC", "adequacy decision", "international transfer", "cross-border"],
                "severity": "critical",
            },
            {
                "id": "gdpr_05",
                "title": "Data Breach Notification (72 hours)",
                "description": "Notification of personal data breach within 72 hours",
                "keywords": ["72 hour", "breach notification", "notify.*authority", "supervisory authority", "data breach"],
                "severity": "critical",
            },
            {
                "id": "gdpr_06",
                "title": "Data Protection Impact Assessment",
                "description": "DPIA required for high-risk processing activities",
                "keywords": ["impact assessment", "DPIA", "privacy impact", "risk assessment"],
                "severity": "high",
            },
            {
                "id": "gdpr_07",
                "title": "Records of Processing",
                "description": "Maintain records of processing activities",
                "keywords": ["record of processing", "processing register", "processing activities"],
                "severity": "medium",
            },
        ],
    },
    "hipaa": {
        "display_name": "HIPAA (Health Insurance Portability and Accountability Act)",
        "jurisdiction": "USA",
        "applies_to": ["healthcare", "pharma", "insurance"],
        "required_clauses": [
            {
                "id": "hipaa_01",
                "title": "Business Associate Agreement",
                "description": "BAA required for any entity handling protected health information",
                "keywords": ["business associate", "BAA", "covered entity", "protected health information", "PHI"],
                "severity": "critical",
            },
            {
                "id": "hipaa_02",
                "title": "PHI Safeguards",
                "description": "Administrative, physical, and technical safeguards for PHI",
                "keywords": ["PHI", "protected health", "safeguard", "health information", "administrative.*technical"],
                "severity": "critical",
            },
            {
                "id": "hipaa_03",
                "title": "Breach Notification",
                "description": "Notification of unauthorized use or disclosure of PHI",
                "keywords": ["breach notification", "unauthorized.*disclosure", "security incident", "breach.*PHI"],
                "severity": "critical",
            },
            {
                "id": "hipaa_04",
                "title": "Minimum Necessary Standard",
                "description": "Access limited to minimum necessary PHI for the purpose",
                "keywords": ["minimum necessary", "need to know", "limited access", "role-based access"],
                "severity": "high",
            },
            {
                "id": "hipaa_05",
                "title": "Return or Destruction of PHI",
                "description": "Return or destroy PHI upon contract termination",
                "keywords": ["return.*PHI", "destroy.*PHI", "return.*health", "destruction.*data"],
                "severity": "high",
            },
        ],
    },
}


def get_applicable_checklists(industry: str) -> list[dict]:
    """Get all compliance checklists applicable to an industry."""
    applicable = []
    ind = (industry or "general").strip().lower()
    if ind == "general":
        return []  # Don't auto-apply all regulations to unknown industries
    for code, checklist in COMPLIANCE_CHECKLISTS.items():
        if ind in checklist["applies_to"]:
            applicable.append({"code": code, **checklist})
    return applicable


def get_checklist(regulation: str) -> dict | None:
    """Get a specific compliance checklist by regulation code."""
    return COMPLIANCE_CHECKLISTS.get(regulation)


def get_all_regulations() -> list[str]:
    """List all available regulation codes."""
    return list(COMPLIANCE_CHECKLISTS.keys())
