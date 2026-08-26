"""
Claustor AI — OpenAI Provider
Primary fast model: gpt-4o-mini (cheap, reliable, no rate limits)
"""
from __future__ import annotations
import time
import structlog
from app.infrastructure.llm.base import (
    BaseLLMProvider, LLMMessage, LLMResponse, LLMProvider
)

logger = structlog.get_logger(__name__)

OPENAI_PRICING = {
    "gpt-4o-mini":  {"input": 0.15,  "output": 0.60},
    "gpt-4o":       {"input": 2.50,  "output": 10.00},
    "gpt-4-turbo":  {"input": 10.00, "output": 30.00},
}

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.default_model = model
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key, timeout=60.0)
            logger.info("openai_provider_initialized")
        except ImportError:
            raise RuntimeError("openai not installed. Run: pip install openai")

    @property
    def provider_type(self) -> LLMProvider:
        return LLMProvider.OPENAI

    async def complete(
        self,
        messages: list[LLMMessage],
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
        max_tokens: int = 2000,
        json_mode: bool = False,
        frequency_penalty: float | None = None,
        logprobs: bool | None = None,
        seed: int | None = None,
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        t0 = time.monotonic()
        try:
            oai_messages = [{"role": m.role, "content": m.content} for m in messages]
            params: dict = dict(
                model=model,
                messages=oai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if json_mode:
                params["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**params)
            latency = int((time.monotonic() - t0) * 1000)
            usage = response.usage
            pricing = OPENAI_PRICING.get(model, {"input": 0.15, "output": 0.60})
            cost_usd = (
                (usage.prompt_tokens / 1_000_000) * pricing["input"] +
                (usage.completion_tokens / 1_000_000) * pricing["output"]
            )
            logger.debug("openai_completion",
                        model=model, latency_ms=latency,
                        input_tokens=usage.prompt_tokens,
                        output_tokens=usage.completion_tokens,
                        cost_usd=round(cost_usd, 6))
            return LLMResponse(
                content=response.choices[0].message.content or "",
                provider=LLMProvider.OPENAI,
                model=model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                latency_ms=latency,
                cost_usd=cost_usd,
            )
        except Exception as e:
            logger.error("openai_completion_failed", model=model, error=str(e))
            raise

    async def is_available(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            models = await self.client.models.list()
            return True
        except Exception:
            return False

    def get_cost_per_1k_tokens(self) -> tuple[float, float]:
        """Return (input_cost, output_cost) per 1K tokens in USD."""
        return (0.00015, 0.00060)  # gpt-4o-mini pricing
