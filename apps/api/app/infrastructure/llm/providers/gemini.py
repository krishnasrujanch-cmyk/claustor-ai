"""Gemini LLM provider — fallback + vision specialist."""

import structlog
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError

from app.infrastructure.llm.base import (
    BaseLLMProvider, LLMMessage, LLMProvider, LLMResponse, LatencyTimer,
)

logger = structlog.get_logger(__name__)

GEMINI_PRICING = {
    "gemini-1.5-flash": (0.000075, 0.000300),
    "gemini-1.5-pro":   (0.001250, 0.005000),
    "gemini-2.0-flash": (0.000100, 0.000400),
}


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini provider.
    Fallback for chat + primary for vision (images/charts).
    """

    def __init__(self, api_key: str, model: str, model_pro: str):
        genai.configure(api_key=api_key)
        self.model_name = model
        self.model_pro_name = model_pro
        self.model = genai.GenerativeModel(model)
        self.model_pro = genai.GenerativeModel(model_pro)

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        json_mode: bool = False,
        use_pro: bool = False,
    ) -> LLMResponse:
        model = self.model_pro if use_pro else self.model
        model_name = self.model_pro_name if use_pro else self.model_name
        timer = LatencyTimer()

        try:
            # Convert messages to Gemini format
            system_parts = []
            history = []
            last_user = ""

            for msg in messages:
                if msg.role == "system":
                    system_parts.append(msg.content)
                elif msg.role == "user":
                    last_user = msg.content
                    if history:
                        history.append({"role": "user", "parts": [msg.content]})
                elif msg.role == "assistant":
                    history.append({"role": "model", "parts": [msg.content]})

            # Prepend system to first user message
            if system_parts and last_user:
                combined = "\n\n".join(system_parts) + "\n\n" + last_user
            else:
                combined = last_user

            gen_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                response_mime_type="application/json" if json_mode else "text/plain",
            )

            response = await model.generate_content_async(
                combined,
                generation_config=gen_config,
            )

            content = response.text
            latency = timer.stop()

            # Gemini doesn't always return token counts on free tier
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            cost = self.calculate_cost(input_tokens, output_tokens)

            logger.debug(
                "gemini_completion",
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency,
            )

            return LLMResponse(
                content=content,
                provider=LLMProvider.GEMINI,
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency,
            )

        except ResourceExhausted as e:
            logger.warning("gemini_rate_limit", error=str(e))
            raise
        except GoogleAPIError as e:
            logger.error("gemini_api_error", error=str(e))
            raise
        except Exception as e:
            logger.error("gemini_unexpected_error", error=str(e))
            raise

    async def is_available(self) -> bool:
        try:
            models = genai.list_models()
            return any(m.name for m in models)
        except Exception:
            return False

    def get_cost_per_1k_tokens(self) -> tuple[float, float]:
        return GEMINI_PRICING.get(self.model_name, (0.000075, 0.000300))
