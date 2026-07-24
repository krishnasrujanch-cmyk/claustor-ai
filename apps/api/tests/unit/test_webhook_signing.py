"""Unit tests for webhook HMAC signing."""
import json
import pytest
from app.api.v1.endpoints.webhooks import sign_payload


def test_sign_payload_returns_string():
    sig = sign_payload("secret", {"event": "test"})
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA-256 hex


def test_sign_payload_deterministic():
    payload = {"event": "contract.analyzed", "id": "123"}
    s1 = sign_payload("secret", payload)
    s2 = sign_payload("secret", payload)
    assert s1 == s2


def test_sign_payload_different_secrets():
    payload = {"event": "test"}
    s1 = sign_payload("secret1", payload)
    s2 = sign_payload("secret2", payload)
    assert s1 != s2


def test_sign_payload_different_payloads():
    s1 = sign_payload("secret", {"event": "a"})
    s2 = sign_payload("secret", {"event": "b"})
    assert s1 != s2


def test_sign_payload_tamper_detection():
    payload = {"event": "contract.analyzed", "data": {"contract_id": "123"}}
    original_sig = sign_payload("secret", payload)

    # Tamper with payload
    payload["data"]["contract_id"] = "456"
    tampered_sig = sign_payload("secret", payload)

    assert original_sig != tampered_sig
