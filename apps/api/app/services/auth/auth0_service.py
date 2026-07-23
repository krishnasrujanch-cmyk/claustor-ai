"""
Claustor AI — Auth0 Service
Handles Auth0 SSO integration.
Validates Auth0 JWTs, syncs user profiles, manages social connections.

Flow:
  1. Frontend redirects to Auth0 login
  2. Auth0 authenticates (Google/Microsoft/email)
  3. Auth0 redirects back with code
  4. We exchange code for tokens
  5. We validate JWT and create/sync user in our DB
  6. We issue our own JWT for API calls
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.domain.models import Organisation, User

logger = structlog.get_logger(__name__)


class Auth0Service:
    """
    Auth0 SSO integration service.
    Handles token validation and user sync.
    """

    def __init__(self):
        self.domain = settings.AUTH0_DOMAIN
        self.client_id = settings.AUTH0_CLIENT_ID
        self.client_secret = settings.AUTH0_CLIENT_SECRET
        self.algorithms = ["RS256"]
        self._jwks_client = None

    def _get_jwks_client(self):
        """Lazy-load JWKS client for JWT validation."""
        if self._jwks_client is None:
            from jose import jwk
            import urllib.request
            import json
            jwks_url = f"https://{self.domain}/.well-known/jwks.json"
            try:
                with urllib.request.urlopen(jwks_url, timeout=10) as response:
                    self._jwks = json.loads(response.read())
            except Exception as e:
                logger.error("jwks_fetch_failed", error=str(e))
                self._jwks = {"keys": []}
        return self._jwks

    async def validate_auth0_token(self, token: str) -> dict:
        """
        Validate Auth0 JWT token.
        Returns decoded payload with user info.
        """
        try:
            from jose import jwt as jose_jwt
            from jose.exceptions import JWTError

            jwks = self._get_jwks_client()

            # Get unverified header to find key
            header = jose_jwt.get_unverified_header(token)
            kid = header.get("kid")

            # Find matching key
            rsa_key = {}
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n":   key["n"],
                        "e":   key["e"],
                    }
                    break

            if not rsa_key:
                raise ValueError("Unable to find RSA key")

            payload = jose_jwt.decode(
                token,
                rsa_key,
                algorithms=self.algorithms,
                audience=self.client_id,
                issuer=f"https://{self.domain}/",
            )
            return payload

        except Exception as e:
            logger.warning("auth0_token_invalid", error=str(e))
            raise ValueError(f"Invalid Auth0 token: {e}")

    async def sync_user(
        self,
        auth0_payload: dict,
        db: AsyncSession,
        org_id=None,
    ) -> User:
        """
        Create or update user from Auth0 payload.
        Called after successful Auth0 authentication.

        Args:
            auth0_payload: Decoded JWT payload from Auth0
            db: DB session
            org_id: Optional — org to add user to

        Returns:
            User model instance
        """
        import uuid

        auth0_sub = auth0_payload.get("sub")       # e.g. "google-oauth2|12345"
        email = auth0_payload.get("email", "")
        name = auth0_payload.get("name", "")

        # Check if user exists by Auth0 sub
        result = await db.execute(
            select(User).where(User.auth0_sub == auth0_sub)
        )
        user = result.scalar_one_or_none()

        if user:
            # Update last active
            from datetime import datetime, timezone
            user.last_active_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("auth0_user_login", user_id=str(user.id), sub=auth0_sub[:20])
            return user

        # Check by email
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if user:
            # Link existing user to Auth0
            user.auth0_sub = auth0_sub
            await db.commit()
            return user

        # Create new user + org
        if not org_id:
            # New signup via SSO — create org
            new_org_id = uuid.uuid4()
            org_name = auth0_payload.get("given_name", email.split("@")[0])
            company = auth0_payload.get(
                "https://claustor.com/company",
                f"{org_name}'s Organisation"
            )
            slug = company.lower().replace(" ", "-")[:50] + f"-{str(new_org_id)[:4]}"

            org = Organisation(
                id=new_org_id,
                name=company,
                slug=slug,
                plan="free",
                max_users=1,
                max_contracts=5,
                max_queries_mo=100,
                pinecone_namespace=f"org_{str(new_org_id).replace('-','')[:8]}",
                gcs_prefix=f"orgs/{new_org_id}",
            )
            db.add(org)
            await db.flush()
            org_id = new_org_id

        user = User(
            org_id=org_id,
            email=email,
            full_name=name,
            auth0_sub=auth0_sub,
            password_hash=None,  # SSO users have no password
            role="super_admin",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info("auth0_user_created", user_id=str(user.id), email=email)
        return user

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        """
        Exchange Auth0 authorization code for tokens.
        Called in the callback route.
        """
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{self.domain}/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    def get_login_url(self, redirect_uri: str, state: str = "") -> str:
        """Generate Auth0 login URL for frontend redirect."""
        from urllib.parse import urlencode
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email",
            "state": state,
        }
        return f"https://{self.domain}/authorize?{urlencode(params)}"


# Singleton
_auth0_service = None


def get_auth0_service() -> Auth0Service:
    global _auth0_service
    if _auth0_service is None:
        _auth0_service = Auth0Service()
    return _auth0_service
