"""Claustor AI — API v1 Router."""

from fastapi import APIRouter
from app.api.v1.endpoints.system import router as system_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.sso import router as sso_router
from app.api.v1.endpoints.contracts import router as contracts_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.billing import router as billing_router
from app.api.v1.endpoints.obligations import router as obligations_router
from app.api.v1.endpoints.alerts import router as alerts_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.api_keys import router as api_keys_router

api_router = APIRouter()

api_router.include_router(system_router,    prefix="/system",    tags=["system"])
api_router.include_router(auth_router,      prefix="/auth",      tags=["auth"])
api_router.include_router(sso_router,       prefix="/sso",       tags=["sso"])
api_router.include_router(contracts_router, prefix="/contracts", tags=["contracts"])
api_router.include_router(chat_router,      prefix="/chat",      tags=["chat"])
api_router.include_router(billing_router,   prefix="/billing",   tags=["billing"])
api_router.include_router(obligations_router, prefix="/obligations", tags=["obligations"])
api_router.include_router(alerts_router,      prefix="/alerts",      tags=["alerts"])
api_router.include_router(analytics_router,   prefix="/analytics",   tags=["analytics"])
api_router.include_router(users_router,     prefix="/users",     tags=["users"])
api_router.include_router(api_keys_router,  prefix="/api-keys",  tags=["api-keys"])
