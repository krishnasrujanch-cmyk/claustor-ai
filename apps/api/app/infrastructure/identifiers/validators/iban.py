"""IBAN checksum validation (MOD 97 algorithm)."""

def validate(value: str) -> bool:
    """Validate IBAN using ISO 13616 MOD 97 check."""
    iban = ''.join(value.split()).upper()
    if len(iban) < 15 or len(iban) > 34:
        return False
    try:
        rearranged = iban[4:] + iban[:4]
        numeric = ''.join(
            str(ord(c) - 55) if c.isalpha() else c
            for c in rearranged
        )
        return int(numeric) % 97 == 1
    except Exception:
        return False

def normalize(value: str) -> str:
    return ''.join(value.split()).upper()
