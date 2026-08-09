"""GSTIN format validation (checksum algorithm varies by state)."""
import re

# State codes valid range: 01-37
VALID_STATE_CODES = set(f"{i:02d}" for i in range(1, 38))
GSTIN_FORMAT = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$')

def validate(value: str) -> bool:
    """Validate GSTIN format and state code."""
    if not value or len(value) != 15:
        return False
    value = value.upper().strip()
    if not GSTIN_FORMAT.match(value):
        return False
    # Check state code validity
    state_code = value[:2]
    return state_code in VALID_STATE_CODES

def normalize(value: str) -> str:
    return value.upper().strip()
