"""Unit tests for plan enforcement / feature gating."""
import pytest
from app.api.v1.middleware.plan_enforcement import check_feature, get_plan_features, FEATURE_PLANS


def test_free_plan_basic_chat():
    assert check_feature("free", "chat") is True


def test_free_plan_no_api_access():
    assert check_feature("free", "api_access") is False


def test_starter_has_ocr():
    assert check_feature("starter", "ocr") is True


def test_starter_no_comparison():
    assert check_feature("starter", "comparison") is False


def test_professional_has_comparison():
    assert check_feature("professional", "comparison") is True


def test_professional_has_webhooks():
    assert check_feature("professional", "webhooks") is True


def test_enterprise_has_sso():
    assert check_feature("enterprise", "sso") is True


def test_enterprise_has_all_features():
    for feature in FEATURE_PLANS:
        assert check_feature("enterprise", feature) is True, f"Enterprise missing: {feature}"


def test_free_plan_features_list():
    features = get_plan_features("free")
    assert "chat" in features
    assert "api_access" not in features


def test_professional_feature_superset_of_starter():
    starter_features = set(get_plan_features("starter"))
    pro_features = set(get_plan_features("professional"))
    assert starter_features.issubset(pro_features)


def test_unknown_feature_defaults_enterprise():
    assert check_feature("free", "nonexistent_feature") is False
    assert check_feature("enterprise", "nonexistent_feature") is True
