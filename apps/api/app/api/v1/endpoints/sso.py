"""
Claustor AI — SSO Endpoints
Auth0 OAuth2 callback, login URL generation.
Social logins: Google, Microsoft.
Enterprise: SAML 2.0, OIDC via Auth0.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import create_access_token
from app.core.config import settings
from app.infrastructure.database.session import get_db
from app.services.auth.auth0_service import get_auth0_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/login")
async def sso_login(
    redirect_uri: str = Query(default=None),
    state: str = Query(default=""),
):
    """
    Generate Auth0 login URL and redirect.
    Frontend calls this to start SSO flow.
    """
    if not settings.AUTH0_DOMAIN:
        raise HTTPException(
            status_code=503,
            detail="SSO not configured. Auth0 domain not set."
        )

    callback_url = redirect_uri or f"{settings.APP_URL}/api/v1/sso/callback"
    auth0 = get_auth0_service()
    login_url = auth0.get_login_url(
        redirect_uri=callback_url,
        state=state,
    )

    return RedirectResponse(url=login_url)


@router.get("/callback")
async def sso_callback(
    code: str = Query(...),
    state: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Auth0 OAuth2 callback.
    Called by Auth0 after user authenticates.
    Exchanges code for tokens, syncs user, returns our JWT.
    """
    if not settings.AUTH0_DOMAIN:
        raise HTTPException(status_code=503, detail="SSO not configured")

    try:
        auth0 = get_auth0_service()
        callback_url = f"{settings.APP_URL}/api/v1/sso/callback"

        # Exchange code for tokens
        tokens = await auth0.exchange_code(
            code=code,
            redirect_uri=callback_url,
        )

        id_token = tokens.get("id_token")
        if not id_token:
            raise ValueError("No ID token in response")

        # Validate and decode token
        payload = await auth0.validate_auth0_token(id_token)

        # Sync user to our DB
        user = await auth0.sync_user(payload, db)

        # Get org plan
        from sqlalchemy import select
        from app.domain.models import Organisation
        org_result = await db.execute(
            select(Organisation.plan).where(Organisation.id == user.org_id)
        )
        plan = org_result.scalar() or "free"

        # Issue our own JWT
        access_token = create_access_token(
            user_id=user.id,
            org_id=user.org_id,
            email=user.email,
            role=user.role,
            plan=plan,
        )

        logger.info("sso_login_success", user_id=str(user.id), email=user.email)

        # Redirect to frontend with token
        frontend_url = f"{settings.APP_URL}/dashboard?token={access_token}"
        if state:
            frontend_url += f"&state={state}"

        return RedirectResponse(url=frontend_url)

    except Exception as e:
        logger.error("sso_callback_failed", error=str(e))
        error_url = f"{settings.APP_URL}/login?error=sso_failed"
        return RedirectResponse(url=error_url)


@router.get("/token")
async def sso_token_exchange(
    auth0_token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange Auth0 token for Claustor JWT.
    Used by frontend SPA (not redirect flow).
    """
    if not settings.AUTH0_DOMAIN:
        raise HTTPException(status_code=503, detail="SSO not configured")

    try:
        auth0 = get_auth0_service()
        payload = await auth0.validate_auth0_token(auth0_token)
        user = await auth0.sync_user(payload, db)

        from sqlalchemy import select
        from app.domain.models import Organisation
        org_result = await db.execute(
            select(Organisation.plan).where(Organisation.id == user.org_id)
        )
        plan = org_result.scalar() or "free"

        access_token = create_access_token(
            user_id=user.id,
            org_id=user.org_id,
            email=user.email,
            role=user.role,
            plan=plan,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": str(user.id),
            "org_id": str(user.org_id),
            "role": user.role,
            "plan": plan,
        }

    except Exception as e:
        logger.error("token_exchange_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid Auth0 token")
