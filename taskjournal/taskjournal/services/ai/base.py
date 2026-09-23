from abc import abstractmethod
from typing import Any

from taskjournal.models.parsed_note import ParsedNote
from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus
from taskjournal.services.ai.prompts import build_daily_prompt, build_prompt

__all__ = ["AIService", "NullAIService", "build_daily_prompt", "build_prompt"]


class AIService(BaseService):
    @abstractmethod
    async def summarize(
        self,
        daily_summaries: list[str],
        stats: dict[str, Any] | None = None,
        is_fireman_week: bool = False,
        period: str = "weekly",
    ) -> str: ...

    @abstractmethod
    async def summarize_day(self, note: ParsedNote) -> str: ...


class NullAIService(AIService):
    @property
    def name(self) -> str:
        return "None"

    def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(
            ServiceStatus.UNCONFIGURED,
            "No AI provider configured — set AI_PROVIDER in .env",
        )

    async def summarize(
        self,
        daily_summaries: list[str],
        stats: dict[str, Any] | None = None,
        is_fireman_week: bool = False,
        period: str = "weekly",
    ) -> str:
        return "AI summaries disabled. Set AI_PROVIDER=claude_code or AI_PROVIDER=openai in .env to enable."

    async def summarize_day(self, note: ParsedNote) -> str:
        return ""
