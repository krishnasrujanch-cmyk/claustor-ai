from fastapi import APIRouter
from app.api.v1.endpoints.system import router as system_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.contracts import router as contracts_router

api_router = APIRouter()
api_router.include_router(system_router,    prefix="/system",    tags=["system"])
api_router.include_router(auth_router,      prefix="/auth",      tags=["auth"])
api_router.include_router(contracts_router, prefix="/contracts", tags=["contracts"])
