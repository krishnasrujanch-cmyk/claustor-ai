"""OpenAI LLM provider — last resort fallback."""

import structlog
from openai import AsyncOpenAI, RateLimitError, APIStatusError

from app.infrastructure.llm.base import (
    BaseLLMProvider, LLMMessage, LLMProvider, LLMResponse, LatencyTimer,
)

logger = structlog.get_logger(__name__)

OPENAI_PRICING = {
    "gpt-4o-mini":  (0.000150, 0.000600),
    "gpt-4o":       (0.002500, 0.010000),
    "gpt-4-turbo":  (0.010000, 0.030000),
}


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI provider — last resort fallback.
    Used when Groq and Gemini both fail.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        timer = LatencyTimer()

        try:
            kwargs = {
                "model": self.model,
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
                "openai_completion",
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=round(cost, 6),
                latency_ms=latency,
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                provider=LLMProvider.OPENAI,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency,
            )

        except RateLimitError as e:
            logger.warning("openai_rate_limit", error=str(e))
            raise
        except APIStatusError as e:
            logger.error("openai_api_error", status=e.status_code, error=str(e))
            raise
        except Exception as e:
            logger.error("openai_unexpected_error", error=str(e))
            raise

    async def is_available(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False

    def get_cost_per_1k_tokens(self) -> tuple[float, float]:
        return OPENAI_PRICING.get(self.model, (0.000150, 0.000600))
