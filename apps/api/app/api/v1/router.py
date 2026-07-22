"""
Claustor AI — API v1 Router
Collects all endpoint routers into one.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    contracts,
    clauses,
    chat,
    organisations,
    users,
    analytics,
    obligations,
    system,
)

api_router = APIRouter()

# ── System ────────────────────────────────────────
api_router.include_router(system.router, prefix="/system", tags=["system"])

# ── Auth ─────────────────────────────────────────
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# ── Organisations ────────────────────────────────
api_router.include_router(organisations.router, prefix="/organisations", tags=["organisations"])

# ── Users ────────────────────────────────────────
api_router.include_router(users.router, prefix="/users", tags=["users"])

# ── Contracts ────────────────────────────────────
api_router.include_router(contracts.router, prefix="/contracts", tags=["contracts"])

# ── Clauses ──────────────────────────────────────
api_router.include_router(clauses.router, prefix="/clauses", tags=["clauses"])

# ── AI Copilot Chat ───────────────────────────────
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

# ── Analytics ────────────────────────────────────
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

# ── Obligations ──────────────────────────────────
api_router.include_router(obligations.router, prefix="/obligations", tags=["obligations"])
