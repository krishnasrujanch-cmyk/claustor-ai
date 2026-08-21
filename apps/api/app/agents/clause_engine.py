"""
Claustor AI — Advanced Clause Engine
Implements all 3 phases of clause intelligence:

Phase 1: Hybrid boundary detection + 25 clause types + missing clause detection
Phase 2: Clause similarity vs playbook + risk score 0-100 + industry weights
Phase 3: Clause relationship mapping + multi-language support
"""

import re
import json
import asyncio
from uuid import UUID
from typing import Any
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


# ─── Clause Type Registry (25 types) ─────────────────────────────────────────

CLAUSE_TYPES = {
    # Financial
    "payment":                  {"label": "Payment Terms",           "category": "financial",    "base_risk": 40},
    "price_adjustment":         {"label": "Price Adjustment",        "category": "financial",    "base_risk": 45},
    "limitation_of_liability":  {"label": "Limitation of Liability", "category": "financial",    "base_risk": 75},
    "indemnification":          {"label": "Indemnification",         "category": "financial",    "base_risk": 80},
    "insurance":                {"label": "Insurance Requirements",  "category": "financial",    "base_risk": 50},
    "escrow":                   {"label": "Escrow",                  "category": "financial",    "base_risk": 35},

    # Operational
    "termination":              {"label": "Termination",             "category": "operational",  "base_risk": 65},
    "auto_renewal":             {"label": "Auto-Renewal",            "category": "operational",  "base_risk": 55},
    "assignment":               {"label": "Assignment",              "category": "operational",  "base_risk": 50},
    "subcontracting":           {"label": "Subcontracting",         "category": "operational",  "base_risk": 45},
    "change_order":             {"label": "Change Order",            "category": "operational",  "base_risk": 40},
    "acceptance_testing":       {"label": "Acceptance Testing",      "category": "operational",  "base_risk": 45},
    "sla":                      {"label": "Service Level Agreement", "category": "operational",  "base_risk": 50},
    "force_majeure":            {"label": "Force Majeure",           "category": "operational",  "base_risk": 40},
    "warranties":               {"label": "Warranties",              "category": "operational",  "base_risk": 55},

    # Legal / Compliance
    "liability":                {"label": "Liability",               "category": "legal",        "base_risk": 75},
    "governing_law":            {"label": "Governing Law",           "category": "legal",        "base_risk": 30},
    "dispute_resolution":       {"label": "Dispute Resolution",      "category": "legal",        "base_risk": 35},
    "representations":          {"label": "Representations",         "category": "legal",        "base_risk": 50},
    "benchmarking":             {"label": "Benchmarking Rights",     "category": "legal",        "base_risk": 30},
    "audit_rights":             {"label": "Audit Rights",            "category": "legal",        "base_risk": 35},

    # IP / Data
    "ip_ownership":             {"label": "IP Ownership",            "category": "ip",           "base_risk": 80},
    "confidentiality":          {"label": "Confidentiality / NDA",   "category": "ip",           "base_risk": 55},
    "data_protection":          {"label": "Data Protection",         "category": "ip",           "base_risk": 65},
    "non_compete":              {"label": "Non-Compete",             "category": "ip",           "base_risk": 70},
    "non_solicitation":         {"label": "Non-Solicitation",        "category": "ip",           "base_risk": 60},
}

# ─── Industry-Specific Risk Weights ──────────────────────────────────────────

INDUSTRY_RISK_WEIGHTS: dict[str, dict[str, float]] = {
    "healthcare": {
        "data_protection":  2.0,   # HIPAA critical
        "liability":        1.8,
        "indemnification":  1.8,
        "insurance":        1.7,
        "sla":              1.5,
    },
    "financial": {
        "data_protection":  2.0,   # GDPR/PCI critical
        "audit_rights":     1.8,
        "liability":        1.8,
        "representations":  1.7,
        "indemnification":  1.6,
    },
    "technology": {
        "ip_ownership":     2.0,   # IP is everything
        "escrow":           1.7,
        "sla":              1.6,
        "data_protection":  1.5,
        "non_compete":      1.5,
    },
    "manufacturing": {
        "warranties":       1.8,
        "liability":        1.7,
        "acceptance_testing":1.6,
        "force_majeure":    1.5,
        "subcontracting":   1.5,
    },
    "retail": {
        "payment":          1.7,
        "auto_renewal":     1.6,
        "assignment":       1.5,
        "price_adjustment": 1.6,
    },
    "general": {
        # No special weights
    },
}

# ─── Expected Clauses by Contract Type ────────────────────────────────────────

EXPECTED_CLAUSES: dict[str, list[str]] = {
    "saas":           ["payment", "sla", "data_protection", "termination", "ip_ownership",
                       "limitation_of_liability", "confidentiality", "auto_renewal"],
    "nda":            ["confidentiality", "non_solicitation", "governing_law",
                       "termination", "dispute_resolution"],
    "msa":            ["payment", "liability", "indemnification", "termination",
                       "governing_law", "confidentiality", "assignment", "audit_rights"],
    "employment":     ["non_compete", "non_solicitation", "ip_ownership",
                       "confidentiality", "termination"],
    "vendor":         ["payment", "warranties", "liability", "termination",
                       "indemnification", "insurance", "audit_rights"],
    "license":        ["ip_ownership", "payment", "termination", "governing_law",
                       "confidentiality", "benchmarking"],
    "outsourcing":    ["sla", "payment", "data_protection", "audit_rights",
                       "termination", "subcontracting", "indemnification"],
    "distribution":   ["payment", "assignment", "non_compete", "termination",
                       "warranties", "liability"],
    "general":        ["payment", "termination", "governing_law", "confidentiality"],
}

# ─── Clause Relationship Map ──────────────────────────────────────────────────

CLAUSE_RELATIONSHIPS: dict[str, list[str]] = {
    "termination":           ["payment", "sla", "data_protection", "escrow"],
    "payment":               ["auto_renewal", "price_adjustment", "termination"],
    "liability":             ["indemnification", "insurance", "limitation_of_liability"],
    "indemnification":       ["liability", "insurance", "warranties"],
    "data_protection":       ["confidentiality", "audit_rights", "sla"],
    "ip_ownership":          ["confidentiality", "non_compete", "assignment", "escrow"],
    "sla":                   ["payment", "termination", "warranties"],
    "assignment":            ["change_of_control", "subcontracting"],
}

# ─── Section Header Patterns (Phase 1) ───────────────────────────────────────

SECTION_PATTERNS = [
    re.compile(r'^\s*(\d+)\.\s{1,4}([A-Z][A-Za-z\s&/,\-]{3,60})\s*$', re.MULTILINE),
    re.compile(r'^\s*(\d+\.\d+)\s{1,4}([A-Z][A-Za-z\s&/,\-]{3,60})\s*$', re.MULTILINE),
    re.compile(r'^\s*(ARTICLE|SECTION|SCHEDULE|EXHIBIT|ANNEX)\s+([A-Z0-9]+)[:\s]+([A-Za-z\s]+)\s*$', re.MULTILINE),
    re.compile(r'^\s*([A-Z][A-Z\s&/]{5,50})\s*$', re.MULTILINE),   # ALL CAPS headers
    re.compile(r'^\s*\(([a-z])\)\s+(.+)$', re.MULTILINE),           # (a) sub-items
]


@dataclass
class DetectedSection:
    """A pre-segmented section from rule-based detection."""
    section_ref: str
    heading: str
    text: str
    start_pos: int
    end_pos: int
    confidence: float = 1.0


@dataclass
class ClauseResult:
    """Fully analyzed clause with all phase data."""
    # Core
    clause_type:        str
    title:              str
    raw_text:           str
    summary:            str
    section_reference:  str

    # Phase 1
    detected_language:  str = "en"
    boundary_method:    str = "hybrid"  # hybrid | llm_only | rule_only

    # Phase 2
    risk_score:         float = 50.0
    risk_level:         str = "medium"
    risk_reason:        str = ""
    industry_weight:    float = 1.0
    adjusted_risk:      float = 50.0
    deviation_from_std: str = ""    # how this differs from standard clause
    playbook_match:     float = 0.0 # 0-1 similarity to org playbook

    # Phase 3
    related_clauses:    list[str] = field(default_factory=list)
    cross_references:   list[str] = field(default_factory=list)  # explicit refs in text


# ─── Phase 1: Hybrid Boundary Detector ───────────────────────────────────────

class HybridBoundaryDetector:
    """
    Detects clause boundaries using rules first, then LLM for classification.
    Much more accurate than pure LLM extraction on long contracts.
    """

    def detect_sections(self, text: str) -> list[DetectedSection]:
        """Rule-based pre-segmentation of contract into sections."""
        sections: list[DetectedSection] = []
        boundaries: list[tuple[int, str, str]] = []  # (pos, ref, heading)

        # Find all section headers
        for pattern in SECTION_PATTERNS[:3]:  # Use first 3 patterns (numbered)
            for match in pattern.finditer(text):
                ref = match.group(1) if len(match.groups()) >= 1 else ""
                heading = match.group(2) if len(match.groups()) >= 2 else match.group(0)
                boundaries.append((match.start(), ref, heading.strip()))

        # Sort by position
        boundaries.sort(key=lambda x: x[0])

        # Remove duplicates (within 50 chars)
        deduped: list[tuple[int, str, str]] = []
        for b in boundaries:
            if not deduped or b[0] - deduped[-1][0] > 50:
                deduped.append(b)

        # Extract text between boundaries
        for i, (pos, ref, heading) in enumerate(deduped):
            start = pos
            end = deduped[i + 1][0] if i + 1 < len(deduped) else len(text)
            section_text = text[start:end].strip()

            if len(section_text) > 30:  # Skip empty sections
                sections.append(DetectedSection(
                    section_ref=ref,
                    heading=heading,
                    text=section_text[:5000],  # Cap each section
                    start_pos=start,
                    end_pos=end,
                    confidence=0.9,
                ))

        logger.info("sections_detected", count=len(sections))
        return sections

    def detect_language(self, text: str) -> str:
        """Simple language detection based on common words."""
        sample = text[:500].lower()
        lang_indicators = {
            "en": ["the", "and", "shall", "agreement", "contract", "party"],
            "hi": ["का", "के", "है", "और", "में", "से"],
            "fr": ["le", "la", "les", "de", "du", "et", "contrat"],
            "de": ["der", "die", "das", "und", "des", "vertrag"],
            "es": ["el", "la", "los", "de", "del", "contrato", "acuerdo"],
        }
        scores: dict[str, int] = {lang: 0 for lang in lang_indicators}
        for lang, words in lang_indicators.items():
            for word in words:
                if f" {word} " in sample:
                    scores[lang] += 1

        return max(scores, key=lambda k: scores[k])


# ─── Phase 2: Playbook Standard Clauses ──────────────────────────────────────

STANDARD_PLAYBOOK: dict[str, str] = {
    "payment": (
        "Payment due within 30 days of invoice. Late payment interest not exceeding 1.5% per month. "
        "Right to withhold payment for disputed invoices."
    ),
    "limitation_of_liability": (
        "Liability capped at 12 months of fees paid. Consequential damages excluded for both parties. "
        "Exceptions for gross negligence, willful misconduct, and IP infringement."
    ),
    "termination": (
        "Either party may terminate with 30 days written notice. Immediate termination for material breach "
        "uncured within 15 days. Data returned within 30 days of termination."
    ),
    "confidentiality": (
        "5-year confidentiality obligation. Standard carve-outs for public domain, independently developed, "
        "and compelled disclosure. No obligation to treat as confidential if received from third party."
    ),
    "sla": (
        "99.9% monthly uptime. Service credits of 10% for each 1% below SLA. "
        "Scheduled maintenance excluded. Credit is sole remedy for SLA breach."
    ),
    "data_protection": (
        "Processor acts only on controller instructions. Sub-processors require written consent. "
        "Data breach notification within 72 hours. Data deletion within 30 days of termination."
    ),
    "ip_ownership": (
        "Each party retains pre-existing IP. Work product ownership stays with creating party. "
        "License granted for term of agreement only. No transfer of IP without written consent."
    ),
    "auto_renewal": (
        "Auto-renews annually unless 60 days written notice of non-renewal. "
        "Price increase notice required 90 days before renewal. Right to terminate at renewal."
    ),
    "indemnification": (
        "Each party indemnifies for own IP infringement claims and gross negligence. "
        "Mutual indemnification for data breaches caused by own negligence. "
        "Indemnification subject to liability cap."
    ),
    "warranties": (
        "Services will conform to documentation. Warranties disclaimed as-is beyond express warranties. "
        "Sole remedy for warranty breach is re-performance or refund."
    ),
}


def compute_playbook_similarity(clause_text: str, clause_type: str) -> tuple[float, str]:
    """
    Simple keyword-based similarity against standard playbook.
    Returns (score 0-1, deviation description).
    """
    standard = STANDARD_PLAYBOOK.get(clause_type, "")
    if not standard:
        return 0.5, "No standard template available"

    # Extract key terms from standard
    std_words = set(re.findall(r'\b\w{4,}\b', standard.lower()))
    clause_words = set(re.findall(r'\b\w{4,}\b', clause_text.lower()))

    if not std_words:
        return 0.5, "Unable to compare"

    overlap = len(std_words & clause_words)
    similarity = overlap / len(std_words)

    # Identify key missing terms (deviations)
    missing_key_terms = []
    important_terms = {
        "payment":               ["30 days", "interest", "disputed"],
        "limitation_of_liability":["cap", "consequential", "excluded"],
        "termination":           ["30 days", "notice", "material breach"],
        "confidentiality":       ["5 years", "carve-out", "public domain"],
        "data_protection":       ["72 hours", "breach", "deletion"],
    }
    for term in important_terms.get(clause_type, []):
        if term.lower() not in clause_text.lower():
            missing_key_terms.append(term)

    deviation = ""
    if missing_key_terms:
        deviation = f"Missing standard terms: {', '.join(missing_key_terms)}"
    elif similarity > 0.7:
        deviation = "Closely matches standard template"
    elif similarity > 0.4:
        deviation = "Partially matches standard template"
    else:
        deviation = "Significantly deviates from standard template"

    return round(similarity, 2), deviation


# ─── Phase 3: Clause Relationship Mapper ─────────────────────────────────────

def map_relationships(clauses: list[ClauseResult]) -> list[ClauseResult]:
    """
    Map relationships between extracted clauses.
    Also detect explicit cross-references in clause text.
    """
    extracted_types = {c.clause_type for c in clauses}

    for clause in clauses:
        # Predefined relationships
        related = CLAUSE_RELATIONSHIPS.get(clause.clause_type, [])
        clause.related_clauses = [r for r in related if r in extracted_types]

        # Detect explicit text references
        cross_refs: list[str] = []
        ref_patterns = [
            r'section\s+(\d+(?:\.\d+)?)',
            r'clause\s+(\d+(?:\.\d+)?)',
            r'article\s+(\d+)',
            r'schedule\s+([A-Z0-9]+)',
        ]
        for pattern in ref_patterns:
            for match in re.finditer(pattern, clause.raw_text, re.IGNORECASE):
                ref = match.group(0)
                if ref not in cross_refs:
                    cross_refs.append(ref)
        clause.cross_references = cross_refs[:5]

    return clauses


# ─── Missing Clause Detector ──────────────────────────────────────────────────

def detect_missing_clauses(
    extracted_types: list[str],
    contract_type: str,
    industry: str = "general",
) -> list[dict]:
    """
    Compare extracted clauses against expected clauses for contract type.
    Returns list of missing clauses with severity.
    """
    normalized_type = contract_type.lower().replace(" ", "_").replace("-", "_")

    # Map common contract type names
    type_map = {
        "vendor":      "vendor",
        "msa":         "msa",
        "master_services_agreement": "msa",
        "saas":        "saas",
        "software":    "saas",
        "subscription":"saas",
        "nda":         "nda",
        "non_disclosure": "nda",
        "employment":  "employment",
        "outsourcing": "outsourcing",
        "license":     "license",
        "distribution":"distribution",
    }

    for key, val in type_map.items():
        if key in normalized_type:
            normalized_type = val
            break

    expected = EXPECTED_CLAUSES.get(normalized_type, EXPECTED_CLAUSES["general"])
    extracted_set = set(extracted_types)

    missing = []
    for clause_type in expected:
        if clause_type not in extracted_set:
            meta = CLAUSE_TYPES.get(clause_type, {})
            # Determine severity
            base_risk = meta.get("base_risk", 50)
            weight = INDUSTRY_RISK_WEIGHTS.get(industry, {}).get(clause_type, 1.0)
            severity = "critical" if base_risk * weight >= 80 else \
                       "high" if base_risk * weight >= 60 else "medium"
            missing.append({
                "clause_type": clause_type,
                "label":       meta.get("label", clause_type),
                "category":    meta.get("category", "general"),
                "severity":    severity,
                "reason":      f"Expected in {normalized_type} contracts but not found",
            })

    return missing


# ─── Main Clause Engine ───────────────────────────────────────────────────────

class ClauseEngine:
    """
    Orchestrates all clause intelligence phases.
    Call analyze() from the pipeline.
    """

    def __init__(self, llm: Any):
        self.llm = llm
        self.detector = HybridBoundaryDetector()

    async def analyze(
        self,
        full_text: str,
        tables: list[dict],
        contract_type: str = "general",
        industry: str = "general",
        contract_value: float | None = None,
    ) -> dict:
        """
        Full clause analysis — all 3 phases.
        Returns: {clauses, missing_clauses, language, summary_stats}
        """
        # ── Phase 1A: Language Detection ──────────────────────────────
        language = self.detector.detect_language(full_text)
        logger.info("language_detected", language=language)

        # ── Phase 1B: Hybrid Boundary Detection ───────────────────────
        sections = self.detector.detect_sections(full_text)

        # If good sections found, classify each separately (more accurate)
        # Otherwise fall back to full-text extraction
        if len(sections) >= 3:
            raw_clauses = await self._classify_sections(sections, contract_type)
        else:
            raw_clauses = await self._extract_full_text(full_text, tables, contract_type)

        logger.info("clauses_extracted", count=len(raw_clauses))

        # ── Phase 1C: Missing Clause Detection ────────────────────────
        extracted_types = [c.get("clause_type", "other") for c in raw_clauses]
        missing = detect_missing_clauses(extracted_types, contract_type, industry)
        logger.info("missing_clauses", count=len(missing))

        # ── Phase 2A: Risk Scoring with Industry Weights ───────────────
        industry_weights = INDUSTRY_RISK_WEIGHTS.get(industry, {})
        scored_clauses = await self._score_risks_advanced(
            raw_clauses, industry_weights, contract_value
        )

        # ── Phase 2B: Playbook Similarity ─────────────────────────────
        results: list[ClauseResult] = []
        for c in scored_clauses:
            ct = c.get("clause_type", "other")
            similarity, deviation = compute_playbook_similarity(
                c.get("raw_text", "") or c.get("summary", ""), ct
            )
            weight = industry_weights.get(ct, 1.0)
            base_score = float(c.get("risk_score", 50))
            adjusted = min(100, base_score * weight)

            result = ClauseResult(
                clause_type=ct,
                title=c.get("title", ""),
                raw_text=c.get("raw_text", "")[:10000],
                summary=c.get("summary", ""),
                section_reference=c.get("section_reference", ""),
                detected_language=language,
                risk_score=base_score,
                risk_level=c.get("risk_level", "medium"),
                risk_reason=c.get("risk_reason", ""),
                industry_weight=weight,
                adjusted_risk=adjusted,
                playbook_match=similarity,
                deviation_from_std=deviation,
            )
            results.append(result)

        # ── Phase 3: Relationship Mapping ─────────────────────────────
        results = map_relationships(results)

        # ── Summary Stats ──────────────────────────────────────────────
        high_count = sum(1 for r in results if r.risk_level == "high")
        med_count  = sum(1 for r in results if r.risk_level == "medium")
        low_count  = sum(1 for r in results if r.risk_level == "low")
        avg_score  = sum(r.adjusted_risk for r in results) / len(results) if results else 0

        return {
            "clauses":         [self._result_to_dict(r) for r in results],
            "missing_clauses": missing,
            "language":        language,
            "stats": {
                "total":       len(results),
                "high_risk":   high_count,
                "medium_risk": med_count,
                "low_risk":    low_count,
                "avg_risk":    round(avg_score, 1),
                "missing":     len(missing),
                "critical_missing": sum(1 for m in missing if m["severity"] == "critical"),
            },
        }

    async def _classify_sections(
        self, sections: list[DetectedSection], contract_type: str
    ) -> list[dict]:
        """Classify pre-detected sections using LLM — more accurate."""
        type_list = ", ".join(CLAUSE_TYPES.keys())

        # Batch sections into groups of 5 for efficiency
        batch_size = 4  # smaller batches with larger text per section
        all_clauses: list[dict] = []

        for i in range(0, len(sections), batch_size):
            batch = sections[i:i + batch_size]
            sections_text = "\n\n---\n\n".join([
                f"SECTION {j+1} (ref: {s.section_ref}, heading: {s.heading}):\n{s.text[:3000]}"
                for j, s in enumerate(batch)
            ])

            prompt = (
                f"Classify these {len(batch)} contract sections. Contract type: {contract_type}\n\n"
                f"{sections_text}\n\n"
                f"For each section return JSON with:\n"
                f"- section_num: 1-{len(batch)}\n"
                f"- clause_type: one of [{type_list}]\n"
                f"- title: descriptive title\n"
                f"- summary: 1-2 sentence summary\n"
                f"- raw_text: the COMPLETE actual clause text verbatim from the contract (no truncation)\n"
                f"- section_reference: the section ref shown above\n\n"
                f"Return ONLY a JSON array of {len(batch)} objects."
            )

            try:
                from app.infrastructure.llm.base import AgentRole, LLMMessage
                response = await self.llm.complete(
                    messages=[
                        LLMMessage(role="system", content="Legal contract analyst. Return only valid JSON."),
                        LLMMessage(role="user", content=prompt),
                    ],
                    role=AgentRole.EXTRACTOR,
                    json_mode=True,
                )
                parsed = json.loads(response.content.strip())
                if isinstance(parsed, dict):
                    for key in ["clauses", "sections", "data", "results"]:
                        if key in parsed:
                            parsed = parsed[key]
                            break
                if isinstance(parsed, list):
                    # Merge section text back
                    for item in parsed:
                        sn = item.get("section_num", 1) - 1
                        if 0 <= sn < len(batch):
                            item.setdefault("raw_text", batch[sn].text[:500])
                        all_clauses.append(item)
            except Exception as e:
                logger.warning("section_classify_error", error=str(e))
                # Fallback: add raw sections as other
                for s in batch:
                    all_clauses.append({
                        "clause_type":      "other",
                        "title":            s.heading,
                        "summary":          s.text[:200],
                        "raw_text":         s.text[:5000],
                        "section_reference":s.section_ref,
                    })

        return all_clauses

    async def _extract_full_text(
        self, text: str, tables: list[dict], contract_type: str
    ) -> list[dict]:
        """
        Iterative clause extraction — works for any document size.
        Splits on structural boundaries (ARTICLE/SECTION), extracts per section,
        merges and deduplicates. No hardcoded text limits.
        """
        import re as _re
        import asyncio as _asyncio
        from app.infrastructure.llm.base import AgentRole, LLMMessage

        type_list = ", ".join(CLAUSE_TYPES.keys())

        # Split on structural boundaries
        boundary_pattern = _re.compile(
            r'(?=\n(?:ARTICLE|SECTION|SCHEDULE|EXHIBIT|ANNEX|APPENDIX|PART|CHAPTER)'
            r'\s+[\dA-Z]+[.:]?)',
            _re.IGNORECASE
        )
        sections = boundary_pattern.split(text)
        sections = [s.strip() for s in sections if s.strip() and len(s.strip()) > 100]

        # If no structural boundaries — sentence-aware sliding window
        if len(sections) <= 1:
            sentences = _re.split(r'(?<=[.!?])\s+', text)
            current, current_len = [], 0
            sections = []
            target_chars = 6000  # ~1500 tokens — safe for any LLM
            for sent in sentences:
                if current_len + len(sent) > target_chars and current:
                    sections.append(" ".join(current))
                    current = current[-20:]  # 20-sentence overlap
                    current_len = sum(len(s) for s in current)
                current.append(sent)
                current_len += len(sent)
            if current:
                sections.append(" ".join(current))

        # Tables as separate sections
        for t in (tables or []):
            t_text = t if isinstance(t, str) else t.get("text", "")
            if t_text.strip():
                sections.append(f"TABLE CONTENT:\n{t_text}")

        logger.info(f"clause_extraction_start: sections={len(sections)} type={contract_type}")

        async def extract_section(section_text: str) -> list[dict]:
            prompt = (
                f"Extract all legal clauses from this {contract_type} contract section.\n\n"
                f"SECTION TEXT:\n{section_text}\n\n"
                f"Return JSON array. Each clause:\n"
                f"- clause_type: one of [{type_list}]\n"
                f"- title: short descriptive title\n"
                f"- summary: 1-2 sentence summary\n"
                f"- raw_text: exact verbatim clause text from the section above\n"
                f"- section_reference: article/section number if visible\n\n"
                f"Return empty [] if no significant clauses found.\n"
                f"Return ONLY valid JSON array."
            )
            try:
                response = await self.llm.complete(
                    messages=[
                        LLMMessage(role="system", content="Legal analyst. Return only valid JSON array."),
                        LLMMessage(role="user", content=prompt),
                    ],
                    role=AgentRole.EXTRACTOR,
                    json_mode=True,
                )
                parsed = json.loads(response.content.strip())
                if isinstance(parsed, dict):
                    for key in ["clauses", "data", "results"]:
                        if key in parsed:
                            return parsed[key]
                return parsed if isinstance(parsed, list) else []
            except Exception as e:
                logger.warning(f"section_clause_error: {e}")
                return []

        # Process sections in batches of 5 concurrently
        all_clauses = []
        for i in range(0, len(sections), 5):
            batch = sections[i:i+5]
            results = await _asyncio.gather(
                *[extract_section(s) for s in batch],
                return_exceptions=True
            )
            for r in results:
                if isinstance(r, list):
                    all_clauses.extend(r)

        # Deduplicate by clause_type + title
        seen, deduped = set(), []
        for clause in all_clauses:
            key = (clause.get("clause_type",""), clause.get("title","")[:40].lower())
            if key not in seen and clause.get("title"):
                seen.add(key)
                deduped.append(clause)

        logger.info(f"clause_extraction_done: clauses={len(deduped)} sections={len(sections)}")
        return deduped


    async def _score_risks_advanced(
        self,
        clauses: list[dict],
        industry_weights: dict[str, float],
        contract_value: float | None,
    ) -> list[dict]:
        """Advanced risk scoring with industry weights and contract value context."""
        if not clauses:
            return []

        clause_list = "\n".join([
            f"{i+1}. [{c.get('clause_type','other').upper()}] {c.get('summary','')[:200]}"
            for i, c in enumerate(clauses)
        ])

        value_ctx = ""
        if contract_value:
            value_ctx = f"\nCONTRACT VALUE: ${contract_value:,.0f} — factor this into risk (higher value = higher stakes)"

        high_risk_types = [k for k,v in CLAUSE_TYPES.items() if v["base_risk"] >= 70]
        industry_ctx = ""
        if industry_weights:
            top = sorted(industry_weights.items(), key=lambda x: x[1], reverse=True)[:3]
            industry_ctx = f"\nINDUSTRY RISK FOCUS: {', '.join(f'{k} (weight {v}x)' for k,v in top)}"

        prompt = (
            f"Score risk for each clause. Return ONLY a JSON array.\n\n"
            f"CLAUSES:\n{clause_list}{value_ctx}{industry_ctx}\n\n"
            f"HIGH RISK clause types: {', '.join(high_risk_types)}\n\n"
            f"Return:\n"
            f'[{{"index":1,"risk_score":75,"risk_level":"high","risk_reason":"reason"}},...]\n\n'
            f"RULES:\n"
            f"- risk_score: 0-100 integer. Use FULL RANGE — do not cluster around 30.\n"
            f"- HIGH (67-100): unlimited liability, unilateral rights, uncapped indemnity, IP transfer\n"
            f"- MEDIUM (34-66): limited caps, auto-renewal, broad confidentiality, short notice periods\n"
            f"- LOW (0-33): standard commercial terms, mutual rights, clear caps\n"
            f"- Return ONLY JSON array, no markdown."
        )

        try:
            from app.infrastructure.llm.base import AgentRole, LLMMessage
            response = await self.llm.complete(
                messages=[
                    LLMMessage(role="system", content="Legal risk analyst. Return only valid JSON."),
                    LLMMessage(role="user", content=prompt),
                ],
                role=AgentRole.REASONER,
                json_mode=True,
            )
            import re as _re
            raw = response.content.strip()
            raw = _re.sub(r"```(?:json)?", "", raw).strip()
            match = _re.search(r"\[.*\]", raw, _re.DOTALL)
            if match:
                raw = match.group(0)
            scores = json.loads(raw)
            if isinstance(scores, dict):
                for key in ["scores", "data", "results", "clauses"]:
                    if key in scores:
                        scores = scores[key]
                        break
            score_map = {s["index"]: s for s in scores if isinstance(s, dict)}
            for i, clause in enumerate(clauses):
                score = score_map.get(i + 1, {})
                clause["risk_score"] = float(score.get("risk_score", 50.0))
                clause["risk_level"] = score.get("risk_level", "medium")
                clause["risk_reason"] = score.get("risk_reason", "")
            return clauses
        except Exception as e:
            logger.warning("risk_scoring_error", error=str(e))
            # Fallback scoring from CLAUSE_TYPES base_risk
            for clause in clauses:
                ct = clause.get("clause_type", "other")
                meta = CLAUSE_TYPES.get(ct, {})
                base = meta.get("base_risk", 50)
                weight = industry_weights.get(ct, 1.0)
                score = min(100, base * weight)
                clause.setdefault("risk_score", float(score))
                clause.setdefault("risk_level",
                    "high" if score >= 67 else "medium" if score >= 34 else "low")
                clause.setdefault("risk_reason", "Auto-scored from clause type")
            return clauses

    def _result_to_dict(self, r: ClauseResult) -> dict:
        return {
            "clause_type":       r.clause_type,
            "title":             r.title,
            "raw_text":          r.raw_text,
            "summary":           r.summary,
            "section_reference": r.section_reference,
            "language":          r.detected_language,
            "boundary_method":   r.boundary_method,
            "risk_score":        r.risk_score,
            "risk_level":        r.risk_level,
            "risk_reason":       r.risk_reason,
            "industry_weight":   r.industry_weight,
            "adjusted_risk":     r.adjusted_risk,
            "playbook_match":    r.playbook_match,
            "deviation":         r.deviation_from_std,
            "related_clauses":   r.related_clauses,
            "cross_references":  r.cross_references,
        }
