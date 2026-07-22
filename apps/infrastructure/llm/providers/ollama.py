"""Ollama provider — on-premise / air-gapped deployments."""

import structlog
import httpx

from app.infrastructure.llm.base import (
    BaseLLMProvider, LLMMessage, LLMProvider, LLMResponse, LatencyTimer,
)

logger = structlog.get_logger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Ollama provider for on-premise deployments.
    No internet required — runs models locally.
    Enable by setting OLLAMA_HOST in .env
    """

    def __init__(self, base_url: str, model: str = "llama3.3:70b"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=120.0,  # local models can be slow
        )

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        timer = LatencyTimer()

        try:
            payload = {
                "model": self.model,
                "messages": [m.to_dict() for m in messages],
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
            if json_mode:
                payload["format"] = "json"

            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            content = data["message"]["content"]
            latency = timer.stop()

            # Ollama returns token counts in eval_count
            input_tokens = data.get("prompt_eval_count", 0)
            output_tokens = data.get("eval_count", 0)

            logger.debug(
                "ollama_completion",
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency,
            )

            return LLMResponse(
                content=content,
                provider=LLMProvider.OLLAMA,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=0.0,  # on-premise = no cost
                latency_ms=latency,
            )

        except httpx.TimeoutException as e:
            logger.error("ollama_timeout", model=self.model, error=str(e))
            raise
        except Exception as e:
            logger.error("ollama_error", model=self.model, error=str(e))
            raise

    async def is_available(self) -> bool:
        try:
            response = await self.client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    def get_cost_per_1k_tokens(self) -> tuple[float, float]:
        return (0.0, 0.0)  # on-premise = free
