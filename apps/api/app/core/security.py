"""Claustor AI — Security Utilities."""

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
    alphabet = string.ascii_letters + string.digits
    raw = f"{prefix}{''.join(secrets.choice(alphabet) for _ in range(40))}"
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()
