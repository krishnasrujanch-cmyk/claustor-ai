"""
Claustor AI — Identifier Extraction Engine
Extracts, validates, normalizes, and resolves identifiers to parties.
"""
from __future__ import annotations
import re
import structlog
from dataclasses import dataclass, field
from typing import Optional

logger = structlog.get_logger()

# ── Country detection patterns ────────────────────────────────────────────────
COUNTRY_SIGNALS = {
    "IN": ["india", "indian", "rupee", "inr", "gstin", "pan no", "cin no",
           "mumbai", "delhi", "bengaluru", "chennai", "hyderabad", "ltd.", "pvt"],
    "GB": ["united kingdom", "england", "scotland", "wales", "sterling", "gbp",
           "companies house", "vat no", "company no", "london", "ltd", "plc"],
    "US": ["united states", "america", "dollar", "usd", "ein", "delaware",
           "new york", "california", "inc.", "corp.", "llc"],
    "AU": ["australia", "australian", "abn", "acn", "aud", "sydney", "melbourne"],
    "SG": ["singapore", "sgd", "uen", "acra"],
    "AE": ["uae", "dubai", "abu dhabi", "aed", "dirham", "trn"],
    "EU": ["european union", "germany", "france", "netherlands", "eur", "euro"],
}


def detect_contract_countries(text: str) -> list[str]:
    """Detect which countries are relevant for this contract."""
    text_lower = text.lower()[:5000]  # check first 5K chars
    detected = []
    for country, signals in COUNTRY_SIGNALS.items():
        score = sum(1 for s in signals if s in text_lower)
        if score >= 2:
            detected.append((country, score))
    detected.sort(key=lambda x: x[1], reverse=True)
    result = [c for c, _ in detected]
    if not result:
        result = ["IN", "GB", "US"]  # default
    return result


# ── Output types ──────────────────────────────────────────────────────────────
@dataclass
class IdentifierMatch:
    type:       str
    label:      str
    value:      str
    country:    str
    confidence: float
    position:   int
    party:      Optional[str] = None
    validated:  bool = False


@dataclass
class ExtractionResult:
    identifiers:       list[IdentifierMatch] = field(default_factory=list)
    party_map:         dict[str, list[IdentifierMatch]] = field(default_factory=dict)
    countries_detected: list[str] = field(default_factory=list)
    summary_text:      str = ""

    def to_searchable_text(self) -> str:
        """Generate human-readable summary for indexing."""
        if not self.identifiers:
            return ""
        lines = ["\n=== REGISTRATION & TAX IDENTIFIERS ==="]
        # Party-mapped first
        for party, ids in self.party_map.items():
            # Clean party name — take only first line, strip junk
            import re as _re
            clean_party = _re.split(r'[\n\r]', party)[0].strip()[:60]
            for id_match in ids:
                conf_str = f"(confidence: {id_match.confidence:.0%})" if id_match.confidence < 0.95 else ""
                lines.append(f"{clean_party} {id_match.label}: {id_match.value} {conf_str}".strip())
        # Unmapped
        unmapped = [i for i in self.identifiers if not i.party]
        for id_match in unmapped:
            lines.append(f"{id_match.label}: {id_match.value}")
        return "\n".join(lines)


# ── Company detection ─────────────────────────────────────────────────────────
COMPANY_PATTERN = re.compile(
    r'([A-Z][A-Za-z\s&\-\.]{4,80}'
    r'(?:Private\s+Limited|Pvt\.?\s*Ltd\.?|Public\s+Limited|Limited|'
    r'LLP|PLC|Inc\.?|LLC|Corp\.?|Bank\s+Limited|Bank\s+Ltd|'
    r'Technologies|Solutions|Services|Group|Holdings))',
    re.IGNORECASE
)


def _find_companies(text: str) -> list[dict]:
    """Find all company names with their positions."""
    companies = []
    seen = set()
    for m in COMPANY_PATTERN.finditer(text):
        # Take only first line of match — remove newline contamination
        name = m.group(1).split("\n")[0].split("\r")[0].strip()
        name_key = re.sub(r"\s+", " ", name).lower()
        if name_key not in seen and len(name) > 8 and not name[0].isdigit():
            seen.add(name_key)
            companies.append({"name": name.strip(), "pos": m.start()})
    return companies


def _map_to_party(id_pos: int, companies: list[dict], window: int = 400) -> Optional[str]:
    """
    Map identifier to nearest company using scoring:
    - Distance (closer = higher score)
    - Before identifier gets priority (company name usually precedes ID)
    """
    if not companies:
        return None
    best_company = None
    best_score   = 0.0
    for co in companies:
        dist = abs(id_pos - co["pos"])
        if dist > window:
            continue
        # Distance score
        distance_score = 1.0 - (dist / window)
        # Bonus: company appears BEFORE the identifier (natural order)
        position_bonus = 0.4 if co["pos"] < id_pos else 0.0
        # Bonus: very close (within 100 chars)
        proximity_bonus = 0.3 if dist < 100 else 0.0
        score = distance_score + position_bonus + proximity_bonus
        if score > best_score:
            best_score   = score
            best_company = co["name"]
    return best_company if best_score > 0.5 else None


# ── Main Engine ───────────────────────────────────────────────────────────────
class IdentifierEngine:
    def __init__(self):
        from app.infrastructure.identifiers.registry import IdentifierRegistry
        self._registry = IdentifierRegistry.get()

    def extract(self, text: str, contract_type: str = "") -> ExtractionResult:
        """
        Full extraction pipeline:
        1. Detect countries
        2. Load relevant patterns
        3. Extract identifiers
        4. Validate + normalize
        5. Map to companies
        6. Generate searchable summary
        """
        result = ExtractionResult()

        # Step 1: Detect countries
        result.countries_detected = detect_contract_countries(text)
        logger.debug("identifier_countries_detected",
                     countries=result.countries_detected)

        # Step 2: Get patterns for detected countries
        patterns = []
        seen_pattern_names = set()
        for country in result.countries_detected:
            for p in self._registry.get_patterns_for_country(country):
                if p.name not in seen_pattern_names:
                    patterns.append(p)
                    seen_pattern_names.add(p.name)
        # Always include global patterns
        for p in self._registry.get_patterns_for_country("GLOBAL"):
            if p.name not in seen_pattern_names:
                patterns.append(p)
                seen_pattern_names.add(p.name)

        # Step 3: Find companies for mapping
        companies = _find_companies(text)

        # Step 4: Extract all identifiers (high priority first)
        seen_values: set[str] = set()
        all_found_values: list[str] = []
        raw_matches = []
        for pattern in patterns:
            for match in pattern.findall(text):
                val = match["value"]
                key = f"{match['type']}:{val}"
                if key in seen_values:
                    continue
                # Skip if this value is a substring of an already-found value
                if any(val in found for found in all_found_values):
                    continue
                # Also remove previously found values that are substrings of this one
                all_found_values = [v for v in all_found_values if v not in val]
                seen_values.add(key)
                all_found_values.append(val)
                raw_matches.append((pattern, match))

        # Step 5: Validate + normalize + map
        for pattern, match in raw_matches:
            value = match["value"]

            # Validate
            is_valid, confidence = self._registry.validate(pattern.name, value)

            # Skip clearly invalid with validator
            if not is_valid and pattern.validate:
                logger.debug("identifier_invalid", type=pattern.name, value=value)
                continue

            # Map to company
            party = _map_to_party(match["position"], companies)

            id_match = IdentifierMatch(
                type       = match["type"],
                label      = match["label"],
                value      = value,
                country    = match["country"],
                confidence = confidence,
                position   = match["position"],
                party      = party,
                validated  = is_valid,
            )
            result.identifiers.append(id_match)

            # Build party map
            if party:
                if party not in result.party_map:
                    result.party_map[party] = []
                result.party_map[party].append(id_match)

        # Sort by priority (position in doc)
        result.identifiers.sort(key=lambda x: x.position)

        # Step 6: Generate searchable text
        result.summary_text = result.to_searchable_text()

        logger.info("identifiers_extracted",
                    total=len(result.identifiers),
                    parties=len(result.party_map),
                    countries=result.countries_detected)

        return result


# ── Singleton ─────────────────────────────────────────────────────────────────
_engine: Optional[IdentifierEngine] = None

def get_identifier_engine() -> IdentifierEngine:
    global _engine
    if _engine is None:
        _engine = IdentifierEngine()
    return _engine
