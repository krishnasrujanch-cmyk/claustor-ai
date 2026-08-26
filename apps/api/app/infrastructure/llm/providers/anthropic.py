"""
Claustor AI — Anthropic/Claude provider.
Used exclusively for the JUDGE role — high-risk clause verification.

Model: claude-sonnet-4-5 (best accuracy for legal analysis)
Pricing: $3/1M input, $15/1M output tokens
"""
import structlog
from app.infrastructure.llm.base import (
    BaseLLMProvider, LLMMessage, LLMProvider, LLMResponse, LatencyTimer,
)

logger = structlog.get_logger(__name__)

ANTHROPIC_PRICING = {
    "claude-sonnet-4-5":    (0.003, 0.015),
    "claude-haiku-4-5":     (0.00025, 0.00125),
}


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude provider.
    Primary use: JUDGE role for high-risk clause verification.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5"):
        self.api_key = api_key
        self.model = model

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        json_mode: bool = False,
        use_fast_model: bool = False,
        **kwargs,
    ) -> LLMResponse:
        import anthropic as _anthropic
        timer = LatencyTimer()

        # Split system message from user/assistant messages
        system_content = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_content = m.content
            elif hasattr(m, "images") and m.images:
                # Vision message with images
                content_parts = []
                for img in m.images:
                    content_parts.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img.get("media_type", "image/jpeg"),
                            "data": img["data"],
                        }
                    })
                content_parts.append({"type": "text", "text": m.content})
                chat_messages.append({"role": m.role, "content": content_parts})
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        # If json_mode, add instruction to system prompt
        if json_mode and system_content:
            system_content += "\n\nYou must respond with valid JSON only. No other text."
        elif json_mode:
            system_content = "You must respond with valid JSON only. No other text."

        try:
            client = _anthropic.AsyncAnthropic(api_key=self.api_key, timeout=60.0)
            kwargs_call = dict(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=chat_messages,
            )
            if system_content:
                kwargs_call["system"] = system_content

            response = await client.messages.create(**kwargs_call)

            content = response.content[0].text
            input_tokens  = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = self.calculate_cost(input_tokens, output_tokens)
            latency = timer.stop()

            logger.debug("anthropic_completion",
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=round(cost, 6),
                latency_ms=latency,
            )

            return LLMResponse(
                content=content,
                provider=LLMProvider.ANTHROPIC,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency,
            )

        except Exception as e:
            logger.error("anthropic_error", model=self.model, error=str(e))
            raise

    async def is_available(self) -> bool:
        try:
            import anthropic as _anthropic
            client = _anthropic.AsyncAnthropic(api_key=self.api_key, timeout=60.0)
            await client.models.list()
            return True
        except Exception:
            return False

    def get_cost_per_1k_tokens(self) -> tuple[float, float]:
        return ANTHROPIC_PRICING.get(self.model, (0.003, 0.015))
