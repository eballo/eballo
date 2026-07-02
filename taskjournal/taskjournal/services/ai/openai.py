from typing import Any

from httpx import AsyncClient, TimeoutException, HTTPStatusError

from taskjournal.services.ai.base import AIService, build_prompt
from taskjournal.services.base import HealthCheckResult, ServiceStatus
from taskjournal.services.logger import logger

_UNCONFIGURED_KEY = "your-openai-api-key"


class OpenAIService(AIService):
    @property
    def name(self) -> str:
        return "OpenAI"

    def health_check(self) -> HealthCheckResult:
        if not self.api_key or self.api_key == _UNCONFIGURED_KEY:
            return HealthCheckResult(
                ServiceStatus.UNCONFIGURED,
                "OPENAI_API_KEY not configured — AI summaries disabled",
            )
        return HealthCheckResult(
            ServiceStatus.OK,
            "API key configured",
        )

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def summarize(
        self,
        daily_summaries: list[str],
        stats: dict[str, Any] | None = None,
        is_fireman_week: bool = False,
        period: str = "weekly",
    ) -> str:
        if not daily_summaries:
            return "No summaries provided."

        prompt = build_prompt(daily_summaries, stats, is_fireman_week, period)
        payload = {
            "model": "gpt-4o-mini",  # fast & cost-effective model
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }

        try:
            async with AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url, headers=self.headers, json=payload
                )
                response.raise_for_status()
                data = response.json()

            choices = data.get("choices")
            if (
                not isinstance(choices, list)
                or not choices
                or "message" not in choices[0]
            ):
                msg = "⚠️ OpenAI service returned an unexpected response format."
                logger.error(msg)
                return msg

            content = choices[0]["message"]["content"]
            if not isinstance(content, str):
                msg = "⚠️ OpenAI service returned an unexpected content format."
                logger.error(msg)
                return msg

            return content.strip()

        except TimeoutException:
            msg = "⚠️ The request to OpenAI timed out. Please try again."
            logger.error(msg)
            return msg
        except HTTPStatusError as e:
            msg = f"⚠️ OpenAI service error: {e.response.status_code} {e.response.reason_phrase}"
            logger.error(msg)
            return msg
        except Exception as e:
            msg = f"⚠️ Failed to summarize due to an unexpected error: {e}"
            logger.error(msg)
            return msg
