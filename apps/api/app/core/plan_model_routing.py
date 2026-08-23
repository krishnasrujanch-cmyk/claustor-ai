"""
Claustor AI — Plan-based LLM Model Routing
Smart complexity-based routing to optimize cost vs quality.

Routing Strategy:
  Free:         Groq only
  Starter:      Groq 80% + Haiku 20%
  Professional: Groq 60% + Haiku 30% + Sonnet 10%
  Enterprise:   Groq 40% + Haiku 30% + Sonnet 30%

Complexity routing (Judge classifies):
  simple  → Groq   (fast, free)
  medium  → Haiku  (good quality, cheap)
  complex → Sonnet (best quality, expensive)

Monthly cost estimates at revised limits:
  Starter:      ₹2,036/org   → ₹7,999 revenue  → 75% margin
  Professional: ₹8,347/org   → ₹29,999 revenue → 72% margin
  Enterprise:   ₹35,000/org  → ₹99,999 revenue → 65% margin
"""
from __future__ import annotations
from enum import Enum


class ModelTier(str, Enum):
    FREE         = "free"
    STARTER      = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE   = "enterprise"


# Complexity → model mapping per plan
COMPLEXITY_ROUTING: dict[str, dict[str, dict]] = {
    "free": {
        "simple":  {"provider": "openai",    "model": "gpt-4o-mini"},
        "medium":  {"provider": "openai",    "model": "gpt-4o-mini"},
        "complex": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
    },
    "starter": {
        "simple":  {"provider": "openai",    "model": "gpt-4o-mini"},
        "medium":  {"provider": "openai",    "model": "gpt-4o-mini"},
        "complex": {"provider": "anthropic", "model": "claude-haiku-4-5"},
    },
    "professional": {
        "simple":  {"provider": "anthropic", "model": "claude-sonnet-4-5"},
        "medium":  {"provider": "anthropic", "model": "claude-sonnet-4-5"},
        "complex": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
    },
    "enterprise": {
        "simple":  {"provider": "anthropic", "model": "claude-sonnet-4-5"},
        "medium":  {"provider": "anthropic", "model": "claude-sonnet-4-5"},
        "complex": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
    },
}

# Base config per plan per role (non-answerer roles)
PLAN_MODEL_CONFIG: dict[str, dict] = {
    "free": {
        "judge":     {"provider": "openai",    "model": "gpt-4o-mini"},
        "extractor": {"provider": "openai",    "model": "gpt-4o-mini"},
        "answerer":  {"provider": "openai",    "model": "gpt-4o-mini"},
        "safety":    {"provider": "openai",    "model": "gpt-4o-mini"},
    },
    "starter": {
        "judge":     {"provider": "openai",    "model": "gpt-4o-mini"},
        "extractor": {"provider": "anthropic", "model": "claude-haiku-4-5"},
        "answerer":  {"provider": "anthropic", "model": "claude-haiku-4-5"},
        "safety":    {"provider": "openai",    "model": "gpt-4o-mini"},
    },
    "professional": {
        "judge":     {"provider": "openai",    "model": "gpt-4o-mini"},
        "extractor": {"provider": "anthropic", "model": "claude-haiku-4-5"},
        "answerer":  {"provider": "anthropic", "model": "claude-haiku-4-5"},  # overridden by complexity
        "safety":    {"provider": "openai",    "model": "gpt-4o-mini"},
    },
    "enterprise": {
        "judge":     {"provider": "anthropic", "model": "claude-haiku-4-5"},
        "extractor": {"provider": "anthropic", "model": "claude-haiku-4-5"},
        "answerer":  {"provider": "anthropic", "model": "claude-sonnet-4-5"},  # overridden by complexity
        "safety":    {"provider": "anthropic", "model": "claude-haiku-4-5"},
    },
}

# Plan limits
PLAN_LIMITS: dict[str, dict] = {
    "free": {
        "max_contracts":   5,
        "max_queries_mo":  100,
        "max_users":       1,
        "max_storage_mb":  50,
    },
    "starter": {
        "max_contracts":   100,
        "max_queries_mo":  5_000,
        "max_users":       5,
        "max_storage_mb":  1_000,
    },
    "professional": {
        "max_contracts":   500,
        "max_queries_mo":  25_000,
        "max_users":       25,
        "max_storage_mb":  10_000,
    },
    "enterprise": {
        "max_contracts":   999_999,   # unlimited
        "max_queries_mo":  999_999,   # unlimited
        "max_users":       999_999,   # unlimited
        "max_storage_mb":  999_999,   # unlimited
    },
}

# Sonnet % per plan (for cost estimation)
SONNET_RATIO: dict[str, float] = {
    "free":         0.00,
    "starter":      0.00,
    "professional": 0.10,
    "enterprise":   0.30,
}

# Cost estimates per org/month at revised limits (INR)
PLAN_AI_COST_INR: dict[str, int] = {
    "free":         12,
    "starter":      2_036,
    "professional": 8_347,
    "enterprise":   35_000,
}

# Pricing (INR/org/month)
PLAN_PRICE_INR: dict[str, int] = {
    "free":         0,
    "starter":      7_999,
    "professional": 29_999,
    "enterprise":   99_999,
}


def get_answerer_for_complexity(plan: str, complexity: str) -> dict:
    """
    Get answerer model based on plan + query complexity.
    complexity: 'simple' | 'medium' | 'complex'
    """
    plan_routing = COMPLEXITY_ROUTING.get(plan, COMPLEXITY_ROUTING["free"])
    return plan_routing.get(complexity, plan_routing["simple"])


def get_plan_providers(plan: str, role: str) -> list[str]:
    """Get ordered provider fallback chain for a plan+role."""
    config = PLAN_MODEL_CONFIG.get(plan, PLAN_MODEL_CONFIG["free"])
    role_config = config.get(role, config.get("answerer", {}))
    primary = role_config.get("provider", "groq")
    fallbacks = {
        "groq":      ["groq", "anthropic"],
        "anthropic": ["anthropic", "groq"],
    }
    return fallbacks.get(primary, ["groq", "anthropic"])


def get_plan_model(plan: str, role: str, complexity: str = "simple") -> str:
    """Get primary model for a plan+role, with complexity routing for answerer."""
    if role == "answerer":
        return get_answerer_for_complexity(plan, complexity).get("model", "llama-3.3-70b-versatile")
    config = PLAN_MODEL_CONFIG.get(plan, PLAN_MODEL_CONFIG["free"])
    role_config = config.get(role, {})
    return role_config.get("model", "llama-3.3-70b-versatile")
