from abc import abstractmethod
from typing import Any

from taskjournal.services.base import BaseService


class AIService(BaseService):
    @abstractmethod
    async def summarize(
        self,
        daily_summaries: list[str],
        stats: dict[str, Any] | None = None,
        is_fireman_week: bool = False,
        period: str = "weekly",
    ) -> str: ...
