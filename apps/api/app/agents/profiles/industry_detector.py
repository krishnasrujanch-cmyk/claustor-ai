"""
Industry Auto-Detector
======================
Detects industry from contract text using keyword matching + LLM fallback.
Runs during pipeline — assigns industry to contract automatically.
"""
import re
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

# Keyword patterns per industry — checked against contract text
INDUSTRY_KEYWORDS = {
    "financial_services": {
        "strong": ["banking", "bank ", "credit facility", "loan agreement",
                   "mortgage", "deposit", "SWIFT", "RTGS", "NEFT", "escrow account",
                   "credit score", "basel", "risk-weighted assets"],
        "moderate": ["RBI", "SEBI", "financial institution", "payment gateway",
                     "settlement", "clearing", "custodian", "portfolio",
                     "treasury", "fund manager", "brokerage", "debenture"],
    },
    "pharma": {
        "strong": ["pharmaceutical", "drug substance", "drug product",
                   "pharmacovigilance", "GMP", "GxP", "clinical study",
                   "API manufacturer", "formulation", "bioequivalence",
                   "CDSCO", "DCGI", "new drug application"],
        "moderate": ["active ingredient", "batch record", "stability study",
                     "shelf life", "excipient", "therapeutic", "dosage form",
                     "pharmacokinetic", "toxicology", "preclinical"],
    },
    "clinical_trials": {
        "strong": ["clinical trial", "clinical study", "investigator",
                   "study protocol", "informed consent", "adverse event",
                   "CRO ", "sponsor ", "IRB", "ethics committee",
                   "phase I", "phase II", "phase III", "phase IV",
                   "ICH-GCP", "randomized", "double-blind"],
        "moderate": ["subject", "patient enrollment", "study site",
                     "case report form", "CRF", "data monitoring",
                     "safety reporting", "DSMB", "endpoint"],
    },
    "healthcare": {
        "strong": ["hospital", "patient", "medical device", "healthcare",
                   "HIPAA", "health insurance", "diagnosis", "treatment",
                   "medical records", "EMR", "EHR", "telemedicine"],
        "moderate": ["clinical", "medical", "health", "care provider",
                     "practitioner", "nursing", "ambulance", "laboratory"],
    },
    "it_saas": {
        "strong": ["SaaS", "software as a service", "cloud service",
                   "API access", "uptime", "source code escrow",
                   "user licence", "subscription", "SOC 2", "ISO 27001",
                   "data center", "availability zone"],
        "moderate": ["software", "platform", "application", "hosting",
                     "deployment", "server", "database", "encryption",
                     "authentication", "backup", "disaster recovery"],
    },
    "manufacturing": {
        "strong": ["manufacturing", "supply chain", "raw material",
                   "bill of materials", "quality inspection", "ISO 9001",
                   "production line", "warehouse", "inventory",
                   "Incoterms", "DDP", "FOB", "CIF"],
        "moderate": ["supplier", "vendor", "procurement", "purchase order",
                     "delivery schedule", "defective", "specification",
                     "batch", "lot number", "packing list"],
    },
    "energy_oil_gas": {
        "strong": ["petroleum", "crude oil", "natural gas", "refinery",
                   "pipeline", "drilling", "upstream", "downstream",
                   "wellhead", "hydrocarbon", "LNG", "PNGRB"],
        "moderate": ["energy", "power plant", "solar", "wind farm",
                     "renewable", "grid", "megawatt", "turbine",
                     "transmission", "distribution", "tariff"],
    },
    "telecom": {
        "strong": ["telecommunications", "telecom", "spectrum",
                   "tower", "BTS", "network infrastructure",
                   "TRAI", "interconnection", "roaming", "5G", "LTE"],
        "moderate": ["bandwidth", "fibre", "broadband", "ISP",
                     "mobile", "wireless", "frequency", "antenna"],
    },
    "government": {
        "strong": ["government of", "ministry of", "tender",
                   "GeM", "GFR", "public procurement", "integrity pact",
                   "Central Vigilance", "CAG audit", "RTI"],
        "moderate": ["government", "public sector", "PSU", "municipal",
                     "department of", "state government", "union territory"],
    },
    "insurance": {
        "strong": ["insurance policy", "premium", "claim settlement",
                   "underwriting", "reinsurance", "IRDAI", "actuary",
                   "policyholder", "sum assured", "surrender value"],
        "moderate": ["insurance", "coverage", "risk assessment",
                     "loss adjuster", "broker", "third party administrator"],
    },
    "media_entertainment": {
        "strong": ["motion picture", "film production", "broadcast",
                   "content licence", "distribution rights", "royalties",
                   "screenplay", "OTT platform", "CBFC", "sequel rights"],
        "moderate": ["media", "entertainment", "content", "streaming",
                     "publishing", "advertising", "production house",
                     "artist", "talent", "copyright"],
    },
    "education": {
        "strong": ["university", "educational institution", "student",
                   "curriculum", "FERPA", "COPPA", "UGC", "AICTE",
                   "edtech", "learning management", "e-learning"],
        "moderate": ["education", "school", "college", "faculty",
                     "academic", "enrollment", "scholarship", "campus"],
    },
    "real_estate": {
        "strong": ["lease agreement", "lease deed", "tenancy",
                   "premises", "landlord", "tenant", "rent escalation",
                   "security deposit", "RERA", "carpet area"],
        "moderate": ["property", "real estate", "building", "floor",
                     "occupancy", "fit-out", "restoration", "sublease"],
    },
    "construction": {
        "strong": ["construction", "civil works", "FIDIC",
                   "bill of quantities", "completion certificate",
                   "retention money", "defects liability period",
                   "variation order", "site possession"],
        "moderate": ["contractor", "subcontractor", "architect",
                     "structural", "foundation", "concrete", "steel",
                     "excavation", "scaffolding", "safety officer"],
    },
}


def detect_industry(text: str, existing_industry: str = "general") -> str:
    """
    Detect industry from contract text using keyword matching.
    Returns the most likely industry code.
    """
    if not text:
        return existing_industry

    text_lower = text.lower()[:20000]  # Check first 20K chars
    scores: dict[str, float] = {}

    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = 0.0
        # Strong matches worth 3 points each
        for kw in keywords.get("strong", []):
            if kw.lower() in text_lower:
                score += 3.0
        # Moderate matches worth 1 point each
        for kw in keywords.get("moderate", []):
            if kw.lower() in text_lower:
                score += 1.0
        if score > 0:
            scores[industry] = score

    if not scores:
        return existing_industry

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_industry, top_score = ranked[0]

    # Require minimum confidence (at least one strong match or 3+ moderate)
    if top_score < 3.0:
        return existing_industry

    logger.info("industry_detected",
                industry=top_industry,
                score=top_score,
                runner_up=ranked[1][0] if len(ranked) > 1 else "none")

    return top_industry


def detect_contract_type_enhanced(text: str, llm_type: str = "Other") -> str:
    """
    Enhance LLM-detected contract type with keyword validation.
    Catches cases where LLM says 'Other' but text clearly indicates a type.
    """
    if llm_type and llm_type != "Other":
        return llm_type

    text_lower = text.lower()[:10000]

    type_patterns = {
        "MSA": ["master services agreement", "master agreement", "services agreement",
                "statement of work", "SOW"],
        "NDA": ["non-disclosure", "confidentiality agreement", "nondisclosure",
                "mutual nda", "unilateral nda"],
        "SLA": ["service level agreement", "service levels", "uptime guarantee",
                "availability target"],
        "Employment": ["employment agreement", "offer letter", "employment contract",
                       "terms of employment", "appointment letter"],
        "Vendor": ["vendor agreement", "supplier agreement", "purchase agreement",
                   "supply agreement", "procurement contract"],
        "License": ["licence agreement", "license agreement", "software licence",
                    "end user licence", "EULA", "licensing terms"],
        "Lease": ["lease agreement", "lease deed", "rental agreement",
                  "tenancy agreement", "licence to occupy"],
        "Loan": ["loan agreement", "credit agreement", "facility agreement",
                 "promissory note", "lending agreement"],
    }

    for contract_type, patterns in type_patterns.items():
        for pattern in patterns:
            if pattern.lower() in text_lower:
                return contract_type

    return llm_type
