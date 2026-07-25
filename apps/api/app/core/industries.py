"""
Claustor AI — Industry Definitions
Risk weights, clause priorities, and pricing by industry.
"""

# Plan definitions with add-on pricing
PLAN_CONFIG = {
    "free": {
        "base_price":     0,
        "addon_price":    0,
        "addon_name":     None,
        "base_industries":["general"],
        "addon_industries":[],
        "has_addon":      False,
        "addon_features": [],
    },
    "starter": {
        "base_price":     3999,
        "addon_price":    1000,
        "addon_name":     "Industry Pack",
        "base_industries":["general"],
        "addon_industries":["general", "it_saas", "manufacturing"],
        "has_addon":      True,
        "addon_features": [
            "IT/SaaS industry risk scoring",
            "Manufacturing/Supply Chain scoring",
            "Industry-specific clause priorities",
        ],
    },
    "professional": {
        "base_price":     16499,
        "addon_price":    2500,
        "addon_name":     "Pro Industry Add-on",
        "base_industries":["general"],
        "addon_industries":["general","pharma","banking","it_saas",
                           "manufacturing","legal","real_estate","hr_employment"],
        "has_addon":      True,
        "addon_features": [
            "All 8 industry risk scoring",
            "Custom clause weight adjustments",
            "Priority processing queue",
            "Dedicated industry playbook templates",
        ],
    },
    "enterprise": {
        "base_price":     0,
        "addon_price":    0,
        "addon_name":     "Everything Included",
        "base_industries":["general","pharma","banking","it_saas",
                          "manufacturing","legal","real_estate","hr_employment"],
        "addon_industries":["general","pharma","banking","it_saas",
                           "manufacturing","legal","real_estate","hr_employment"],
        "has_addon":      False,
        "addon_features": [
            "All 8 industries",
            "Custom clause weights",
            "Dedicated workers",
            "White-label options",
            "SLA guarantee",
        ],
    },
}

# Which plans can access each industry (base only)
INDUSTRY_PLAN_ACCESS = {
    "general":      ["free", "starter", "professional", "enterprise"],
    "it_saas":      ["starter", "professional", "enterprise"],
    "manufacturing":["starter", "professional", "enterprise"],
    "hr_employment":["professional", "enterprise"],
    "legal":        ["professional", "enterprise"],
    "real_estate":  ["professional", "enterprise"],
    "pharma":       ["professional", "enterprise"],
    "banking":      ["professional", "enterprise"],
}

INDUSTRIES = {
    "general": {
        "label":       "General / Other",
        "description": "Standard contract analysis",
        "premium_inr": 0,
        "icon":        "📄",
        "min_plan":    "free",
        "keywords":    [],
        "high_risk_clauses": ["liability", "indemnification", "termination"],
        "critical_missing":  ["liability", "termination", "governing_law"],
        "risk_multipliers": {},
    },
    "pharma": {
        "label":       "Pharma / Life Sciences",
        "description": "FDA/CDSCO compliance, IP exclusivity, clinical data",
        "premium_inr": 3000,
        "icon":        "💊",
        "keywords":    ["fda", "cdsco", "clinical", "pharmaceutical", "drug", "license",
                        "distribution agreement", "royalt", "biotech", "medicorp", "biopharma",
                        "therapeutic", "patent", "exclusiv", "territory", "licensee", "licensor"],
        "high_risk_clauses": [
            "ip_ownership", "ip_exclusivity", "indemnification",
            "liability", "termination", "minimum_performance",
            "product_liability", "regulatory_compliance",
        ],
        "critical_missing": [
            "liability", "ip_ownership", "regulatory_compliance",
            "product_liability", "termination",
        ],
        "risk_multipliers": {
            "ip_ownership":          1.3,   # exclusivity = higher risk
            "indemnification":       1.4,   # product liability = critical
            "minimum_performance":   1.2,
            "regulatory_compliance": 1.5,
        },
    },
    "banking": {
        "label":       "Banking / Finance",
        "description": "RBI/SEBI compliance, data residency, AML/KYC",
        "premium_inr": 5000,
        "icon":        "🏦",
        "keywords":    ["rbi", "sebi", "nbfc", "bank", "loan", "credit", "financial",
                        "aml", "kyc", "capital", "deposit", "lending", "npa", "basel"],
        "high_risk_clauses": [
            "data_residency", "regulatory_reporting", "audit_rights",
            "liability", "indemnification", "kyc_aml",
        ],
        "critical_missing": [
            "data_residency", "audit_rights", "regulatory_reporting",
            "liability", "governing_law",
        ],
        "risk_multipliers": {
            "data_residency":       1.5,
            "regulatory_reporting": 1.4,
            "audit_rights":         1.3,
            "indemnification":      1.3,
        },
    },
    "it_saas": {
        "label":       "IT / SaaS",
        "description": "SLA, IP rights, vendor lock-in, source code escrow",
        "premium_inr": 0,
        "icon":        "💻",
        "keywords":    ["software", "saas", "api", "uptime", "sla", "source code",
                        "cloud", "platform", "subscription", "integration", "devops"],
        "high_risk_clauses": [
            "sla", "ip_ownership", "liability", "data_portability",
            "termination", "auto_renewal",
        ],
        "critical_missing": [
            "sla", "liability", "ip_ownership", "data_portability",
            "termination",
        ],
        "risk_multipliers": {
            "sla":              1.3,
            "data_portability": 1.4,
            "ip_ownership":     1.2,
            "auto_renewal":     1.2,
        },
    },
    "manufacturing": {
        "label":       "Manufacturing / Supply Chain",
        "description": "Quality standards, volume commitments, force majeure",
        "premium_inr": 1500,
        "icon":        "🏭",
        "keywords":    ["manufacturing", "supply chain", "purchase order", "quality",
                        "delivery", "warehouse", "logistics", "vendor", "supplier",
                        "raw material", "production"],
        "high_risk_clauses": [
            "minimum_order", "quality_standards", "force_majeure",
            "exclusivity", "liability", "indemnification",
        ],
        "critical_missing": [
            "quality_standards", "force_majeure", "liability",
            "termination", "governing_law",
        ],
        "risk_multipliers": {
            "exclusivity":      1.3,
            "force_majeure":    1.2,
            "minimum_order":    1.2,
        },
    },
    "legal": {
        "label":       "Legal / Professional Services",
        "description": "Retainer terms, conflicts, privilege, billing",
        "premium_inr": 2000,
        "icon":        "⚖️",
        "keywords":    ["legal", "attorney", "counsel", "retainer", "law firm",
                        "privilege", "conflict", "litigation", "arbitration"],
        "high_risk_clauses": [
            "conflict_of_interest", "privilege", "liability",
            "indemnification", "termination",
        ],
        "critical_missing": [
            "conflict_of_interest", "liability", "termination",
            "confidentiality", "governing_law",
        ],
        "risk_multipliers": {
            "conflict_of_interest": 1.5,
            "privilege":            1.4,
            "liability":            1.2,
        },
    },
    "real_estate": {
        "label":       "Real Estate / Lease",
        "description": "Rent escalation, exit clauses, force majeure",
        "premium_inr": 1500,
        "icon":        "🏢",
        "keywords":    ["lease", "rent", "property", "landlord", "tenant", "premises",
                        "real estate", "office space", "commercial"],
        "high_risk_clauses": [
            "rent_escalation", "exit_clause", "force_majeure",
            "maintenance", "liability",
        ],
        "critical_missing": [
            "exit_clause", "force_majeure", "maintenance",
            "liability", "governing_law",
        ],
        "risk_multipliers": {
            "rent_escalation": 1.3,
            "exit_clause":     1.4,
            "force_majeure":   1.2,
        },
    },
    "hr_employment": {
        "label":       "HR / Employment",
        "description": "Non-compete, IP assignment, termination, benefits",
        "premium_inr": 1000,
        "icon":        "👥",
        "keywords":    ["employment", "employee", "salary", "non-compete",
                        "non-solicitation", "termination", "severance", "benefits"],
        "high_risk_clauses": [
            "non_compete", "ip_ownership", "termination",
            "confidentiality", "non_solicitation",
        ],
        "critical_missing": [
            "non_compete", "ip_ownership", "termination",
            "confidentiality",
        ],
        "risk_multipliers": {
            "non_compete":     1.4,
            "ip_ownership":    1.3,
            "non_solicitation":1.2,
        },
    },
}

INDUSTRY_CHOICES = [
    {"id": k, "label": v["label"], "icon": v["icon"],
     "description": v["description"], "premium_inr": v["premium_inr"],
     "min_plan": v.get("min_plan", "free"),
     "allowed_plans": INDUSTRY_PLAN_ACCESS.get(k, ["professional", "enterprise"])}
    for k, v in INDUSTRIES.items()
]


def detect_industry(text: str) -> str:
    """Auto-detect industry from contract text."""
    text_lower = text.lower()
    scores = {}
    for industry_id, industry in INDUSTRIES.items():
        if industry_id == "general":
            continue
        score = sum(1 for kw in industry["keywords"] if kw in text_lower)
        if score > 0:
            scores[industry_id] = score
    if not scores:
        return "general"
    return max(scores, key=scores.get)


def get_industry_risk_multiplier(industry_id: str, clause_type: str) -> float:
    """Get risk multiplier for a clause type in a given industry."""
    industry = INDUSTRIES.get(industry_id, INDUSTRIES["general"])
    return industry["risk_multipliers"].get(clause_type, 1.0)


def get_plan_price(base_plan: str, addon_enabled: bool = False) -> dict:
    """Calculate price for plan with optional add-on."""
    config = PLAN_CONFIG.get(base_plan, PLAN_CONFIG["free"])
    base   = config["base_price"]
    addon  = config["addon_price"] if addon_enabled else 0
    total  = base + addon

    return {
        "base_plan":       base_plan,
        "base_price":      base,
        "addon_price":     config["addon_price"],
        "addon_enabled":   addon_enabled,
        "addon_name":      config["addon_name"],
        "addon_features":  config["addon_features"],
        "total":           total,
        "total_gst":       round(total * 1.18),
        "display":         f"₹{total:,}/month" if total > 0 else "Custom",
        "has_addon":       config["has_addon"],
        "active_industries": config["addon_industries"] if addon_enabled else config["base_industries"],
    }
