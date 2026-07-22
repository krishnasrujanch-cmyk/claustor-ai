"""
Claustor AI — Configuration Management
All settings loaded from environment variables.
Never hardcode secrets — always use .env
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Validated at startup — app fails fast if required values missing.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    APP_VERSION: str = "0.1.0"
    APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        if self.ENVIRONMENT == "production":
            return ["https://claustor.com", "https://www.claustor.com"]
        return ["http://localhost:3000", "http://localhost:8000"]

    # ── Database ─────────────────────────────────
    DATABASE_URL: str
    DATABASE_URL_TEST: str = ""
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # ── Redis ────────────────────────────────────
    REDIS_URL: str
    REDIS_TTL_SESSION: int = 7200       # 2 hours
    REDIS_TTL_PERMISSIONS: int = 300    # 5 minutes
    REDIS_TTL_ANALYTICS: int = 900      # 15 minutes
    REDIS_TTL_EMBEDDING: int = 86400    # 24 hours

    # ── Vector DB (Pinecone) ─────────────────────
    PINECONE_API_KEY: str
    PINECONE_INDEX: str = "claustor-contracts"
    PINECONE_HOST: str = ""

    # ── Message Queue ─────────────────────────────
    RABBITMQ_URL: str = ""  # empty = use Redis

    @property
    def USE_RABBITMQ(self) -> bool:
        return bool(self.RABBITMQ_URL)

    # ── GCS ──────────────────────────────────────
    GCP_PROJECT: str = ""
    GCP_REGION: str = "asia-south1"
    GCS_BUCKET_CONTRACTS: str = "claustor-contracts"
    GCS_BUCKET_CACHE: str = "claustor-cache"

    # ── Auth (Auth0) ──────────────────────────────
    AUTH0_DOMAIN: str = ""
    AUTH0_CLIENT_ID: str = ""
    AUTH0_CLIENT_SECRET: str = ""
    AUTH0_ISSUER_BASE_URL: str = ""

    # JWT (internal)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── LLM Providers ─────────────────────────────
    # Primary: Groq
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_FAST: str = "llama-3.1-8b-instant"

    # Fallback: Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_MODEL_PRO: str = "gemini-1.5-pro"

    # Last resort: OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # On-premise: Ollama
    OLLAMA_HOST: str = ""          # empty = disabled
    OLLAMA_MODEL: str = "llama3.3:70b"

    @property
    def LLM_FALLBACK_CHAIN(self) -> list[str]:
        """Active providers in priority order."""
        chain = []
        if self.GROQ_API_KEY:
            chain.append("groq")
        if self.GEMINI_API_KEY:
            chain.append("gemini")
        if self.OPENAI_API_KEY:
            chain.append("openai")
        if self.OLLAMA_HOST:
            chain.append("ollama")
        return chain

    # ── Email (Resend) ────────────────────────────
    RESEND_API_KEY: str = ""
    RESEND_FROM: str = "hello@claustor.com"
    RESEND_FROM_NAME: str = "Claustor AI"

    # ── Billing ───────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""

    # ── Monitoring ────────────────────────────────
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "claustor-ai"
    SENTRY_DSN: str = ""

    # ── Security ──────────────────────────────────
    BCRYPT_ROUNDS: int = 12
    API_KEY_PREFIX: str = "clst_live_"
    MAX_UPLOAD_SIZE_MB: int = 50
    RATE_LIMIT_LOGIN: str = "10/minute"

    # ── Plan Limits ───────────────────────────────
    PLAN_LIMITS: dict = {
        "free": {
            "users": 1, "contracts": 5, "queries": 100,
            "storage_mb": 100, "workers": 1, "extra_users": 0,
        },
        "starter": {
            "users": 10, "contracts": 100, "queries": 5000,
            "storage_mb": 10240, "workers": 2, "extra_users": 10,
        },
        "professional": {
            "users": 50, "contracts": 1000, "queries": 50000,
            "storage_mb": 102400, "workers": 3, "extra_users": 50,
        },
        "enterprise": {
            "users": -1, "contracts": -1, "queries": -1,
            "storage_mb": -1, "workers": 5, "extra_users": -1,
        },
    }

    # ── Validators ────────────────────────────────
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        import re
        if not v:
            raise ValueError("DATABASE_URL is required")
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Strip sslmode and channel_binding — asyncpg uses connect_args instead
        v = re.sub(r"[?&]sslmode=[^&]*", "", v)
        v = re.sub(r"[?&]channel_binding=[^&]*", "", v)
        v = re.sub(r"[?&]$", "", v)
        v = re.sub(r"\?$", "", v)
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v:
            raise ValueError("REDIS_URL is required")
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v

    @model_validator(mode="after")
    def validate_llm_providers(self) -> "Settings":
        if not any([self.GROQ_API_KEY, self.GEMINI_API_KEY,
                    self.OPENAI_API_KEY, self.OLLAMA_HOST]):
            raise ValueError(
                "At least one LLM provider must be configured: "
                "GROQ_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY, or OLLAMA_HOST"
            )
        return self

    @model_validator(mode="after")
    def validate_pinecone(self) -> "Settings":
        if not self.PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY is required")
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — singleton pattern."""
    return Settings()


# Global settings instance
settings = get_settings()
# Note: DATABASE_URL in .env should be:
# postgresql+asyncpg://user:pass@host/db
# WITHOUT sslmode or channel_binding params
# SSL is handled via connect_args in session.py
