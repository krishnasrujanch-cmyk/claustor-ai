"""
Claustor AI — Identifier Registry
Loads and compiles all identifier patterns from YAML files.
Patterns are precompiled at startup — NOT per document.
"""
from __future__ import annotations
import re
import importlib
import structlog
from pathlib import Path
from typing import Optional

logger = structlog.get_logger()

# ── Pattern Entry ─────────────────────────────────────────────────────────────
class IdentifierPattern:
    def __init__(self, name: str, config: dict, country: str):
        self.name        = name
        self.label       = config.get("label", name)
        self.country     = country
        self.priority    = config.get("priority", 50)
        self.validate    = config.get("validate", False)
        self.normalize   = config.get("normalize", "uppercase")
        self.description = config.get("description", "")
        # Precompile regex
        try:
            self._regex = re.compile(config["regex"])
        except re.error as e:
            logger.warning("identifier_pattern_compile_error", name=name, error=str(e))
            self._regex = None

    def findall(self, text: str) -> list[dict]:
        if not self._regex:
            return []
        results = []
        for m in self._regex.finditer(text):
            value = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
            value = self._normalize(value)
            if not value:
                continue
            results.append({
                "type":        self.name,
                "label":       self.label,
                "value":       value,
                "country":     self.country,
                "priority":    self.priority,
                "position":    m.start(),
                "raw":         m.group(0),
            })
        return results

    def _normalize(self, value: str) -> str:
        if not value:
            return ""
        mode = self.normalize
        if mode == "uppercase":
            return value.upper().strip()
        if mode == "digits_only":
            return re.sub(r'\D', '', value)
        if mode == "remove_spaces":
            return re.sub(r'\s+', '', value).upper()
        return value.strip()


# ── Registry ──────────────────────────────────────────────────────────────────
class IdentifierRegistry:
    _instance: Optional["IdentifierRegistry"] = None

    def __init__(self):
        self._patterns: list[IdentifierPattern] = []
        self._validators: dict = {}
        self._country_patterns: dict[str, list[IdentifierPattern]] = {}
        self._loaded = False

    @classmethod
    def get(cls) -> "IdentifierRegistry":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.load()
        return cls._instance

    def load(self):
        """Load all YAML pattern files and precompile."""
        try:
            import yaml
        except ImportError:
            logger.warning("pyyaml_not_installed — using fallback patterns")
            self._load_fallback()
            return

        patterns_dir = Path(__file__).parent / "patterns"
        if not patterns_dir.exists():
            logger.warning("patterns_dir_not_found", path=str(patterns_dir))
            self._load_fallback()
            return

        for yml_file in sorted(patterns_dir.glob("*.yml")):
            try:
                with open(yml_file) as f:
                    data = yaml.safe_load(f)
                country = data.get("country", "GLOBAL")
                for name, config in (data.get("patterns") or {}).items():
                    pattern = IdentifierPattern(name, config, country)
                    self._patterns.append(pattern)
                    if country not in self._country_patterns:
                        self._country_patterns[country] = []
                    self._country_patterns[country].append(pattern)
            except Exception as e:
                logger.warning("pattern_file_load_error", file=str(yml_file), error=str(e))

        # Load validators
        validators_dir = Path(__file__).parent / "validators"
        if validators_dir.exists():
            for py_file in validators_dir.glob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                    mod  = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "validate"):
                        self._validators[py_file.stem.upper()] = mod
                        # Also register by common aliases
                        aliases = {
                            "UK_VAT": ["UK_VAT", "VAT"],
                            "GSTIN": ["GSTIN"],
                            "PAN": ["PAN"],
                            "ABN": ["ABN", "AU_ABN"],
                            "IBAN": ["IBAN"],
                        }
                        for key, names in aliases.items():
                            if py_file.stem.upper() == key.replace("_", "").replace("UK", "UK_"):
                                for n in names:
                                    self._validators[n] = mod
                except Exception as e:
                    logger.warning("validator_load_error", file=py_file.stem, error=str(e))

        self._loaded = True
        logger.info("identifier_registry_loaded",
                    patterns=len(self._patterns),
                    validators=len(self._validators),
                    countries=list(self._country_patterns.keys()))

    def _load_fallback(self):
        """Minimal fallback patterns if YAML not available."""
        fallback = {
            "GSTIN": (r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b", "IN", 100),
            "CIN":   (r"\b([UL][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6})\b", "IN", 95),
            "PAN":   (r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", "IN", 90),
            "UK_VAT":(r"\b(GB\s?[0-9]{9})\b", "GB", 100),
            "US_EIN":(r"\b([0-9]{2}-[0-9]{7})\b", "US", 100),
        }
        for name, (regex, country, priority) in fallback.items():
            p = IdentifierPattern(name, {
                "regex": regex, "priority": priority,
                "label": name, "validate": False, "normalize": "uppercase"
            }, country)
            self._patterns.append(p)
        self._loaded = True

    def validate(self, id_type: str, value: str) -> tuple[bool, float]:
        """Validate identifier value. Returns (is_valid, confidence)."""
        mod = self._validators.get(id_type)
        if not mod:
            return True, 0.8  # no validator = assume valid, lower confidence
        try:
            is_valid = mod.validate(value)
            return is_valid, 0.99 if is_valid else 0.1
        except Exception:
            return True, 0.7

    def get_patterns_for_country(self, country: str) -> list[IdentifierPattern]:
        """Get patterns relevant for a specific country + global patterns."""
        result = self._country_patterns.get("GLOBAL", [])
        if country and country.upper() in self._country_patterns:
            result = result + self._country_patterns[country.upper()]
        return sorted(result, key=lambda p: p.priority, reverse=True)

    @property
    def all_patterns(self) -> list[IdentifierPattern]:
        return sorted(self._patterns, key=lambda p: p.priority, reverse=True)
