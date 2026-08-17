"""Claustor AI - Viewer Restriction Loader.
Loads masking patterns from YAML config - no hardcoding.
"""
from __future__ import annotations
import re
import structlog
from pathlib import Path
from functools import lru_cache

logger = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def _load_patterns() -> list[dict]:
    """Load viewer restriction patterns from YAML config."""
    try:
        import yaml
        path = Path(__file__).parent / "config" / "viewer_restrictions.yml"
        with open(path) as f:
            data = yaml.safe_load(f)
        return data.get("viewer_restricted_patterns", [])
    except Exception as e:
        logger.warning("viewer_restrictions_load_failed", error=str(e))
        return []


def mask_viewer_response(text: str) -> str:
    """
    Mask sensitive data from LLM response for Viewer role.
    Patterns loaded from viewer_restrictions.yml - no hardcoding.
    Add new patterns to YAML without touching this file.
    """
    patterns = _load_patterns()
    result = text
    for p in patterns:
        try:
            result = re.sub(
                p["pattern"],
                p["replacement"],
                result,
                flags=re.IGNORECASE,
            )
        except re.error as e:
            logger.warning("viewer_mask_error",
                           name=p.get("name"), error=str(e))
    return result


def get_viewer_system_prompt() -> str:
    """Return system prompt addition for Viewer role."""
    patterns = _load_patterns()
    id_names = ", ".join(
        p["name"] for p in patterns
        if "AMOUNT" not in p["name"] and "IFSC" not in p["name"]
    )
    return f"""

IMPORTANT - VIEWER MODE ACTIVE:
This user has Viewer role with restricted data access.
Do NOT reveal in your response:
- Exact monetary values, contract amounts, or payment figures
- Party identifiers: {id_names}
- Bank account numbers, IFSC codes, or payment details
- Penalty amounts or exact credit percentages

Instead use:
- For monetary values: say [Amount Restricted - contact Admin]
- For identifiers: say [ID Restricted - contact Admin]
- For risk details: give only High/Medium/Low level summary
- Focus on clause summaries, dates, and obligations only
"""
