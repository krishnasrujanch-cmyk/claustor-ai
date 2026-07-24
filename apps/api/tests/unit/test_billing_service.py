"""Unit tests for billing service plan definitions."""
import pytest
from app.services.billing.billing_service import PLANS


def test_all_plans_exist():
    assert "free" in PLANS
    assert "starter" in PLANS
    assert "professional" in PLANS
    assert "enterprise" in PLANS


def test_free_plan_limits():
    free = PLANS["free"]
    assert free["contracts"] == 5
    assert free["queries"] == 100
    assert free["users"] == 1


def test_starter_plan_limits():
    starter = PLANS["starter"]
    assert starter["contracts"] == 100
    assert starter["queries"] == 5000
    assert starter["users"] == 10


def test_professional_plan_limits():
    pro = PLANS["professional"]
    assert pro["contracts"] == 1000
    assert pro["queries"] == 50000
    assert pro["users"] == 50


def test_enterprise_unlimited():
    ent = PLANS["enterprise"]
    assert ent["contracts"] == -1
    assert ent["queries"] == -1
    assert ent["users"] == -1


def test_plan_hierarchy():
    """Professional should have more than starter."""
    assert PLANS["professional"]["contracts"] > PLANS["starter"]["contracts"]
    assert PLANS["professional"]["queries"] > PLANS["starter"]["queries"]
    assert PLANS["professional"]["users"] > PLANS["starter"]["users"]


def test_all_plans_have_features():
    for plan_name, plan in PLANS.items():
        assert "features" in plan, f"{plan_name} missing features"
        assert isinstance(plan["features"], list)
