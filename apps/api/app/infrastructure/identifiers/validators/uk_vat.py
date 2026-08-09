"""UK VAT checksum validation (modulus 97 algorithm)."""

def validate(value: str) -> bool:
    """Validate UK VAT number using standard algorithm."""
    digits = ''.join(c for c in value.replace('GB', '') if c.isdigit())
    if len(digits) not in (9, 12):
        return False
    try:
        weights = [8, 7, 6, 5, 4, 3, 2]
        nums = [int(d) for d in digits[:7]]
        total = sum(w * n for w, n in zip(weights, nums))
        check = int(digits[7:9])
        # Try standard modulus 97 check
        if (total % 97) == check:
            return True
        # Try alternative modulus 97-55
        if ((total + 55) % 97) == check:
            return True
        return False
    except Exception:
        return False

def normalize(value: str) -> str:
    return 'GB' + ''.join(c for c in value.replace('GB', '') if c.isdigit())
