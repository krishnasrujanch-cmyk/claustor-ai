"""
Claustor AI — Security Utilities
Centralised password hashing, verification, token generation.
All password operations go through here — never call bcrypt directly.
"""

import hashlib
import secrets
import string

import bcrypt


def hash_password(password: str) -> str:
    """
    Hash password with bcrypt.
    Pre-hashes with SHA-256 to bypass bcrypt 72-byte limit.
    SHA-256 output = 64 hex chars = always safe.
    """
    pre_hashed = hashlib.sha256(password.encode("utf-8")).hexdigest().encode("utf-8")
    return bcrypt.hashpw(pre_hashed, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    pre_hashed = hashlib.sha256(plain.encode("utf-8")).hexdigest().encode("utf-8")
    return bcrypt.checkpw(pre_hashed, hashed.encode("utf-8"))


def generate_api_key(prefix: str = "clst_live_") -> tuple[str, str]:
    """
    Generate a secure API key.
    Returns (raw_key, key_hash) — store only the hash.
    raw_key shown to user once, never stored.
    """
    alphabet = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(40))
    raw_key = f"{prefix}{random_part}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash


def generate_invite_token() -> str:
    """Generate secure random token for user invitations."""
    return secrets.token_urlsafe(32)


def hash_ip(ip: str) -> str:
    """
    Hash IP address for audit log storage.
    GDPR compliant — never store raw IPs.
    """
    return hashlib.sha256(ip.encode()).hexdigest()
