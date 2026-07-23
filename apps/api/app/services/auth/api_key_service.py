"""
Claustor AI — API Key Service
Manages API keys for Professional+ plans.
Keys: clst_live_xxxx (prod) | clst_test_xxxx (dev)
Storage: SHA-256 hash only — raw key shown once, never stored.
"""

import hashlib
import secrets
import string
from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import APIKey, Organisation

logger = structlog.get_logger(__name__)

# Key format
LIVE_PREFIX = "clst_live_"
TEST_PREFIX = "clst_test_"
KEY_LENGTH  = 40  # random chars after prefix

# Scopes available
VALID_SCOPES = {
    "contracts:read",
    "contracts:write",
    "contracts:delete",
    "chat:read",
    "chat:write",
    "analytics:read",
    "users:read",
    "users:write",
}


class APIKeyService:
    """
    API key management service.
    Keys are hashed before storage — raw key shown once only.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_key(self, is_test: bool = False) -> tuple[str, str, str]:
        """
        Generate a new API key.
        Returns (raw_key, key_hash, key_prefix)
        raw_key shown to user once — never stored.
        key_hash stored in DB for verification.
        key_prefix stored for identification (clst_live_xxxxx...)
        """
        prefix = TEST_PREFIX if is_test else LIVE_PREFIX
        alphabet = string.ascii_letters + string.digits
        random_part = "".join(secrets.choice(alphabet) for _ in range(KEY_LENGTH))
        raw_key = f"{prefix}{random_part}"
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        key_prefix = raw_key[:16] + "..."  # Show first 16 chars
        return raw_key, key_hash, key_prefix

    async def create_key(
        self,
        org_id: UUID,
        user_id: UUID,
        name: str,
        scopes: list[str],
        expires_at: datetime | None = None,
        is_test: bool = False,
    ) -> dict:
        """
        Create a new API key.
        Returns raw key — shown ONCE, not stored.

        Args:
            org_id:     Organisation ID
            user_id:    User creating the key
            name:       Human-readable name ("Production key", "CI/CD key")
            scopes:     List of permissions (["contracts:read", "chat:write"])
            expires_at: Optional expiry date
            is_test:    True = test key (clst_test_), False = live key (clst_live_)
        """
        # Validate scopes
        invalid_scopes = set(scopes) - VALID_SCOPES
        if invalid_scopes:
            raise ValueError(f"Invalid scopes: {invalid_scopes}. Valid: {VALID_SCOPES}")

        if not scopes:
            raise ValueError("At least one scope required")

        # Check key limit per org (max 10)
        result = await self.db.execute(
            select(APIKey).where(
                APIKey.org_id == org_id,
                APIKey.is_active == True,
            )
        )
        existing_keys = result.scalars().all()
        if len(existing_keys) >= 10:
            raise ValueError("Maximum 10 API keys per organisation")

        raw_key, key_hash, key_prefix = self._generate_key(is_test)

        api_key = APIKey(
            org_id=org_id,
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes,
            expires_at=expires_at,
            is_active=True,
        )
        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)

        logger.info(
            "api_key_created",
            org_id=str(org_id),
            user_id=str(user_id),
            name=name,
            scopes=scopes,
            key_id=str(api_key.id),
        )

        return {
            "id": str(api_key.id),
            "name": name,
            "key": raw_key,         # ← shown ONCE, never again
            "key_prefix": key_prefix,
            "scopes": scopes,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_at": api_key.created_at.isoformat(),
            "warning": "Save this key securely. It will not be shown again.",
        }

    async def verify_key(self, raw_key: str) -> dict | None:
        """
        Verify an API key and return org/scope info.
        Called on every API request using key auth.
        Returns None if key invalid/expired/revoked.
        """
        if not raw_key.startswith((LIVE_PREFIX, TEST_PREFIX)):
            return None

        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

        result = await self.db.execute(
            select(
                APIKey.id,
                APIKey.org_id,
                APIKey.user_id,
                APIKey.scopes,
                APIKey.expires_at,
                APIKey.is_active,
                APIKey.name,
            ).where(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,
            )
        )
        key = result.first()

        if not key:
            return None

        # Check expiry
        if key.expires_at and key.expires_at < datetime.now(timezone.utc):
            logger.warning("api_key_expired", key_id=str(key.id))
            return None

        # Get org plan
        org_result = await self.db.execute(
            select(Organisation.plan).where(Organisation.id == key.org_id)
        )
        plan = org_result.scalar() or "free"

        # Update last used
        await self.db.execute(
            update(APIKey)
            .where(APIKey.id == key.id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await self.db.commit()

        return {
            "key_id":  str(key.id),
            "org_id":  str(key.org_id),
            "user_id": str(key.user_id),
            "scopes":  key.scopes,
            "plan":    plan,
            "name":    key.name,
        }

    async def list_keys(self, org_id: UUID) -> list[dict]:
        """List all API keys for an org (without raw keys)."""
        result = await self.db.execute(
            select(APIKey).where(
                APIKey.org_id == org_id,
                APIKey.is_active == True,
            ).order_by(APIKey.created_at.desc())
        )
        keys = result.scalars().all()

        return [
            {
                "id": str(k.id),
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "created_at": k.created_at.isoformat(),
            }
            for k in keys
        ]

    async def revoke_key(self, key_id: UUID, org_id: UUID) -> bool:
        """Revoke an API key. Returns True if found and revoked."""
        result = await self.db.execute(
            select(APIKey).where(
                APIKey.id == key_id,
                APIKey.org_id == org_id,
                APIKey.is_active == True,
            )
        )
        key = result.scalar_one_or_none()
        if not key:
            return False

        key.is_active = False
        await self.db.commit()

        logger.info("api_key_revoked", key_id=str(key_id), org_id=str(org_id))
        return True

    def check_scope(self, key_info: dict, required_scope: str) -> bool:
        """Check if API key has required scope."""
        scopes = key_info.get("scopes", [])
        return required_scope in scopes or "admin" in scopes
