"""Groq LLM provider — primary provider for Claustor AI."""

import structlog
from groq import AsyncGroq, RateLimitError, APIStatusError

from app.infrastructure.llm.base import (
    BaseLLMProvider, LLMMessage, LLMProvider, LLMResponse, LatencyTimer,
)

logger = structlog.get_logger(__name__)

# Groq model pricing (per 1K tokens, USD) — as of 2026
GROQ_PRICING = {
    "llama-3.3-70b-versatile":  (0.00059, 0.00079),
    "llama-3.1-70b-versatile":  (0.00059, 0.00079),
    "llama-3.1-8b-instant":     (0.00005, 0.00008),
    "llama-3.3-8b-instant":     (0.00005, 0.00008),
}


class GroqProvider(BaseLLMProvider):
    """
    Groq LLM provider.
    Primary provider — fastest inference, free tier generous.
    Used for: extraction (8b), reasoning (70b), chat (70b).
    """

    def __init__(self, api_key: str, model: str, model_fast: str):
        self.client = AsyncGroq(api_key=api_key)
        self.model = model              # llama-3.3-70b-versatile
        self.model_fast = model_fast    # llama-3.1-8b-instant

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        json_mode: bool = False,
        use_fast_model: bool = False,
    ) -> LLMResponse:
        """Send messages to Groq and return completion."""
        model = self.model_fast if use_fast_model else self.model
        timer = LatencyTimer()

        try:
            kwargs = {
                "model": model,
                "messages": [m.to_dict() for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**kwargs)

            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = self.calculate_cost(input_tokens, output_tokens)
            latency = timer.stop()

            logger.debug(
                "groq_completion",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=round(cost, 6),
                latency_ms=latency,
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                provider=LLMProvider.GROQ,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency,
            )

        except RateLimitError as e:
            logger.warning("groq_rate_limit", model=model, error=str(e))
            raise
        except APIStatusError as e:
            logger.error("groq_api_error", model=model, status=e.status_code, error=str(e))
            raise
        except Exception as e:
            logger.error("groq_unexpected_error", model=model, error=str(e))
            raise

    async def is_available(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False

    def get_cost_per_1k_tokens(self) -> tuple[float, float]:
        return GROQ_PRICING.get(self.model, (0.00059, 0.00079))
