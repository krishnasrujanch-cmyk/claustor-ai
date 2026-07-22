"""
Claustor AI — LLM Router
Central routing for all LLM calls.
Handles: fallback chain, circuit breaker, role-based routing, cost tracking.

To migrate from Groq to Gemini:
  Set GROQ_API_KEY= empty in .env
  Router auto-detects and uses Gemini as primary.
  Zero code changes required.
"""

import asyncio
import time
from uuid import UUID

import structlog

from app.core.config import settings
from app.infrastructure.llm.base import (
    AgentRole, BaseLLMProvider, LLMMessage,
    LLMProvider, LLMResponse,
)
from app.infrastructure.llm.providers.groq import GroqProvider
from app.infrastructure.llm.providers.gemini import GeminiProvider

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """
    Circuit breaker per provider.
    CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing) → CLOSED
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "CLOSED"

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                "circuit_opened",
                failures=self.failure_count,
                threshold=self.failure_threshold,
            )

    @property
    def is_open(self) -> bool:
        if self.state == "CLOSED":
            return False
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if (self.last_failure_time and
                    time.monotonic() - self.last_failure_time > self.recovery_timeout):
                self.state = "HALF_OPEN"
                logger.info("circuit_half_open")
                return False
            return True
        return False  # HALF_OPEN — allow one test request


class AllProvidersFailedError(Exception):
    """Raised when all providers in the fallback chain fail."""
    pass


class LLMRouter:
    """
    Central router for all LLM calls in Claustor AI.

    Usage:
        router = LLMRouter()
        response = await router.complete(
            messages=[LLMMessage(role="user", content="...")],
            role=AgentRole.EXTRACTOR,
            org_id=org_id,
        )

    Provider selection:
        - Reads GROQ_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY from config
        - Empty key = provider disabled
        - Fallback chain determined by LLM_FALLBACK_CHAIN config
    """

    # Role → preferred providers (first available in list wins)
    ROLE_PROVIDER_MAP: dict[AgentRole, list[LLMProvider]] = {
        AgentRole.SAFETY_GUARD: [LLMProvider.GROQ, LLMProvider.GEMINI],
        AgentRole.EXTRACTOR:    [LLMProvider.GROQ, LLMProvider.GEMINI],
        AgentRole.REASONER:     [LLMProvider.GROQ, LLMProvider.GEMINI, LLMProvider.OPENAI],
        AgentRole.JUDGE:        [LLMProvider.GROQ, LLMProvider.GEMINI, LLMProvider.OPENAI],
        AgentRole.ANSWERER:     [LLMProvider.GROQ, LLMProvider.GEMINI, LLMProvider.OPENAI],
        AgentRole.VISION:       [LLMProvider.GEMINI],   # Gemini only for vision
        AgentRole.NEGOTIATOR:   [LLMProvider.GROQ, LLMProvider.GEMINI, LLMProvider.OPENAI],
    }

    # Roles that use the fast/cheap model (8b)
    FAST_MODEL_ROLES = {AgentRole.SAFETY_GUARD, AgentRole.EXTRACTOR}

    def __init__(self):
        self.providers: dict[LLMProvider, BaseLLMProvider] = {}
        self.circuit_breakers: dict[LLMProvider, CircuitBreaker] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize available providers from config."""

        if settings.GROQ_API_KEY:
            self.providers[LLMProvider.GROQ] = GroqProvider(
                api_key=settings.GROQ_API_KEY,
                model=settings.GROQ_MODEL,
                model_fast=settings.GROQ_MODEL_FAST,
            )
            logger.info("llm_provider_registered", provider="groq", model=settings.GROQ_MODEL)

        if settings.GEMINI_API_KEY:
            self.providers[LLMProvider.GEMINI] = GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL,
                model_pro=settings.GEMINI_MODEL_PRO,
            )
            logger.info("llm_provider_registered", provider="gemini", model=settings.GEMINI_MODEL)

        # Initialize circuit breakers for all registered providers
        for provider in self.providers:
            self.circuit_breakers[provider] = CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=60,
            )

        if not self.providers:
            raise RuntimeError("No LLM providers configured. Check your .env file.")

        logger.info(
            "llm_router_initialized",
            providers=list(self.providers.keys()),
            fallback_chain=settings.LLM_FALLBACK_CHAIN,
        )

    def _get_chain(self, role: AgentRole) -> list[LLMProvider]:
        """Get ordered provider chain for this role."""
        preferred = self.ROLE_PROVIDER_MAP.get(role, list(self.providers.keys()))
        # Filter to only registered + non-open-circuit providers
        return [p for p in preferred if p in self.providers]

    async def complete(
        self,
        messages: list[LLMMessage],
        role: AgentRole,
        org_id: UUID | None = None,
        json_mode: bool = False,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Route completion request through provider chain.
        Tries each provider in order, skipping open circuits.
        """
        chain = self._get_chain(role)
        use_fast = role in self.FAST_MODEL_ROLES
        last_error: Exception | None = None

        for provider_type in chain:
            breaker = self.circuit_breakers[provider_type]

            if breaker.is_open:
                logger.debug("circuit_open_skip", provider=provider_type.value)
                continue

            provider = self.providers[provider_type]

            try:
                logger.debug(
                    "llm_attempt",
                    provider=provider_type.value,
                    role=role.value,
                    use_fast=use_fast,
                )

                response = await provider.complete(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )

                breaker.record_success()

                # Track cost per org (async, non-blocking)
                if org_id:
                    asyncio.create_task(
                        self._track_cost(org_id, response)
                    )

                logger.info(
                    "llm_success",
                    provider=provider_type.value,
                    role=role.value,
                    tokens=response.total_tokens,
                    cost_usd=round(response.cost_usd, 6),
                    latency_ms=response.latency_ms,
                )

                return response

            except Exception as e:
                last_error = e
                breaker.record_failure()
                logger.warning(
                    "llm_provider_failed",
                    provider=provider_type.value,
                    role=role.value,
                    error=str(e),
                    trying_next=True,
                )
                continue

        raise AllProvidersFailedError(
            f"All LLM providers failed for role {role.value}. "
            f"Last error: {last_error}"
        )

    async def _track_cost(self, org_id: UUID, response: LLMResponse) -> None:
        """Track LLM cost per org in Redis (non-blocking)."""
        try:
            from app.infrastructure.database.redis import get_redis
            redis = await get_redis()
            from datetime import datetime
            month = datetime.now().strftime("%Y-%m")
            key = f"llm_cost:{org_id}:{month}"
            await redis.incrbyfloat(key, response.cost_usd)
            await redis.expire(key, 35 * 86400)  # 35 days
        except Exception as e:
            # Cost tracking is non-critical — never fail the main request
            logger.warning("cost_tracking_failed", org_id=str(org_id), error=str(e))

    async def get_provider_status(self) -> dict:
        """Get health status of all providers."""
        status = {}
        for provider_type, breaker in self.circuit_breakers.items():
            status[provider_type.value] = {
                "state": breaker.state,
                "failures": breaker.failure_count,
                "available": not breaker.is_open,
            }
        return status


# Singleton router instance
_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    """Get or create the singleton LLM router."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
