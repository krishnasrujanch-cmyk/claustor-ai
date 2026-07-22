"""
Claustor AI — LLM Abstraction Layer
All LLM calls go through this interface.
Never import Groq/Gemini/OpenAI directly in business logic.
Migrating providers = change config, zero code changes.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator


class LLMProvider(str, Enum):
    GROQ    = "groq"
    GEMINI  = "gemini"
    OPENAI  = "openai"
    OLLAMA  = "ollama"   # on-premise


class AgentRole(str, Enum):
    """Each role uses a different model — cheap for simple, best for complex."""
    SAFETY_GUARD = "safety_guard"   # 8b — fast, cheap
    EXTRACTOR    = "extractor"      # 8b — structured JSON
    REASONER     = "reasoner"       # 70b — complex CoT
    JUDGE        = "judge"          # 70b — quality check
    ANSWERER     = "answerer"       # 70b — user-facing
    VISION       = "vision"         # Gemini — images/charts
    NEGOTIATOR   = "negotiator"     # 70b — clause suggestions


@dataclass
class LLMMessage:
    role: str       # "system" | "user" | "assistant"
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMResponse:
    content: str
    provider: LLMProvider
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    cached: bool = False
    metadata: dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class BaseLLMProvider(ABC):
    """
    Abstract base for all LLM providers.
    Implement this interface to add a new provider.
    Everything else in the codebase uses this interface only.
    """

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Send messages and get completion."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is reachable."""
        ...

    @abstractmethod
    def get_cost_per_1k_tokens(self) -> tuple[float, float]:
        """Returns (input_cost_per_1k, output_cost_per_1k) in USD."""
        ...

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a completion."""
        input_cost, output_cost = self.get_cost_per_1k_tokens()
        return (input_tokens / 1000 * input_cost) + (output_tokens / 1000 * output_cost)

    def _measure_latency(self) -> "LatencyTimer":
        return LatencyTimer()


class LatencyTimer:
    """Context manager for measuring latency."""

    def __init__(self):
        self.start = time.perf_counter()
        self.elapsed_ms = 0

    def stop(self) -> int:
        self.elapsed_ms = int((time.perf_counter() - self.start) * 1000)
        return self.elapsed_ms
