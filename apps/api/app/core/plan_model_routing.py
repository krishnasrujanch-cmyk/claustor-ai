"""
Claustor AI — Plan-based LLM Model Routing
Maps user plans to appropriate models balancing cost vs quality.

Free:         Groq only     → ₹8/user/month
Starter:      Groq + Haiku  → ₹40/user/month  
Professional: Groq + Sonnet → ₹150/user/month
Enterprise:   Anthropic all → ₹500/user/month
"""

from __future__ import annotations
from enum import Enum


class ModelTier(str, Enum):
    FREE         = "free"
    STARTER      = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE   = "enterprise"


# Model selection per plan per role
PLAN_MODEL_CONFIG: dict[str, dict] = {
    "free": {
        "judge":     {"provider": "groq",      "model": "llama-3.3-70b-versatile"},
        "extractor": {"provider": "groq",      "model": "llama-3.1-8b-instant"},
        "answerer":  {"provider": "groq",      "model": "llama-3.3-70b-versatile"},
        "safety":    {"provider": "groq",      "model": "llama-3.1-8b-instant"},
    },
    "starter": {
        "judge":     {"provider": "groq",      "model": "llama-3.3-70b-versatile"},
        "extractor": {"provider": "anthropic", "model": "claude-haiku-3-5"},
        "answerer":  {"provider": "anthropic", "model": "claude-haiku-3-5"},
        "safety":    {"provider": "groq",      "model": "llama-3.1-8b-instant"},
    },
    "professional": {
        "judge":     {"provider": "groq",      "model": "llama-3.3-70b-versatile"},
        "extractor": {"provider": "anthropic", "model": "claude-haiku-3-5"},
        "answerer":  {"provider": "anthropic", "model": "claude-sonnet-4-5"},
        "safety":    {"provider": "groq",      "model": "llama-3.1-8b-instant"},
    },
    "enterprise": {
        "judge":     {"provider": "anthropic", "model": "claude-sonnet-4-5"},
        "extractor": {"provider": "anthropic", "model": "claude-sonnet-4-5"},
        "answerer":  {"provider": "anthropic", "model": "claude-sonnet-4-5"},
        "safety":    {"provider": "anthropic", "model": "claude-haiku-3-5"},
    },
}

# Cost estimates per plan (INR/user/month)
PLAN_AI_COST_INR = {
    "free":         8,
    "starter":      40,
    "professional": 150,
    "enterprise":   500,
}


def get_plan_providers(plan: str, role: str) -> list[str]:
    """
    Get ordered list of providers for a given plan and role.
    Returns fallback chain e.g. ["anthropic", "groq"]
    """
    config = PLAN_MODEL_CONFIG.get(plan, PLAN_MODEL_CONFIG["free"])
    role_config = config.get(role, config.get("answerer", {}))
    primary = role_config.get("provider", "groq")

    # Always add fallback
    fallbacks = {
        "groq":      ["groq", "anthropic"],
        "anthropic": ["anthropic", "groq"],
    }
    return fallbacks.get(primary, ["groq", "anthropic"])


def get_plan_model(plan: str, role: str) -> str:
    """Get the primary model for a given plan and role."""
    config = PLAN_MODEL_CONFIG.get(plan, PLAN_MODEL_CONFIG["free"])
    role_config = config.get(role, {})
    return role_config.get("model", "llama-3.3-70b-versatile")
