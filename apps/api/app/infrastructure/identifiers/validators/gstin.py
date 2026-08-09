"""GSTIN checksum validation."""

def validate(value: str) -> bool:
    """
    Validate GSTIN using checksum algorithm.
    GSTIN = 2 (state) + 10 (PAN) + 1 (entity) + 1 (Z) + 1 (checksum)
    """
    if not value or len(value) != 15:
        return False
    value = value.upper().strip()
    CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    try:
        total = 0
        for i, ch in enumerate(value[:-1]):
            if ch not in CHARS:
                return False
            digit = CHARS.index(ch)
            if i % 2 == 1:
                digit *= 2
            total += digit // 36 + digit % 36
        checksum = (36 - (total % 36)) % 36
        expected = CHARS[checksum]
        return value[-1] == expected
    except Exception:
        return False

def normalize(value: str) -> str:
    return value.upper().strip()
