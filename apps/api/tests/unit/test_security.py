"""Unit tests for security utilities."""
import pytest
from app.core.security import hash_password, verify_password, generate_invite_token, hash_ip


def test_hash_password_returns_string():
    hashed = hash_password("TestPassword123!")
    assert isinstance(hashed, str)
    assert len(hashed) > 0


def test_hash_password_not_plaintext():
    hashed = hash_password("TestPassword123!")
    assert hashed != "TestPassword123!"


def test_verify_password_correct():
    password = "TestPassword123!"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("TestPassword123!")
    assert verify_password("WrongPassword!", hashed) is False


def test_hash_password_different_salts():
    p = "SamePassword"
    h1 = hash_password(p)
    h2 = hash_password(p)
    assert h1 != h2  # bcrypt generates different salts


def test_generate_invite_token_length():
    token = generate_invite_token()
    assert len(token) >= 32


def test_generate_invite_token_unique():
    t1 = generate_invite_token()
    t2 = generate_invite_token()
    assert t1 != t2


def test_hash_ip():
    ip = "192.168.1.1"
    hashed = hash_ip(ip)
    assert hashed != ip
    assert len(hashed) == 64  # SHA-256 hex
    assert hash_ip(ip) == hash_ip(ip)  # deterministic
