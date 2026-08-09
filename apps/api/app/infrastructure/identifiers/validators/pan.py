"""PAN format validation (no checksum — format only)."""
import re

PAN_PATTERN = re.compile(r'^[A-Z]{3}[ABCFGHLJPTF][A-Z][0-9]{4}[A-Z]$')

def validate(value: str) -> bool:
    """
    Validate PAN format:
    - 4th char: A=Individual, B=HUF, C=Company, F=Firm, 
                G=Govt, H=HUF, L=Local, J=AOP, P=Individual,
                T=Trust, F=Firm
    """
    if not value or len(value) != 10:
        return False
    return bool(PAN_PATTERN.match(value.upper().strip()))

def normalize(value: str) -> str:
    return value.upper().strip()
