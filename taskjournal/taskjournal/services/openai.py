from typing import Any

import httpx

from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus
from taskjournal.services.logger import logger
from taskjournal.services.time import TimeService

_UNCONFIGURED_KEY = "your-openai-api-key"


class OpenAIService(BaseService):
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
        """
        Summarize daily notes into a single summary.

        Args:
            daily_summaries: List of daily summaries
            stats: Statistics (total time, days at office/home, vacation days)
            is_fireman_week: Whether the week was a fireman week
            period: 'weekly' or 'monthly'
        """
        if not daily_summaries:
            return "No summaries provided."

        system_message = (
            "You are an expert Senior Software Engineer assistant. "
            f"Your task is to generate a professional, clear, and high-impact {period} work summary. "
            "The summary MUST follow this structure:\n"
            "1. **Summary**: A brief (2-3 sentences) cohesive overview of the period's most important outcomes.\n"
            "2. **Specific Sections**: Use bullet points for the following categories if applicable:\n"
            "- **Key Achievements** (Focus on high-level impact and delivered value)\n"
            "- **Technical Debt & Refactoring** (Infrastructure improvements and code quality)\n"
            "- **Problems Fixed & Critical Bugs** (Technical challenges overcome)\n"
            "- **Collaboration & Mentoring** (Cross-team support, code reviews, and knowledge sharing)\n"
            "- **Strategic Decisions & Research** (Architectural choices or technology investigations)\n"
            "- **Upcoming Focus** (Brief preview of next period's priorities)\n"
            "Keep the specific sections concise using bullet points. Do not write paragraphs for them. "
            "Focus on technical progress, blockers encountered, and important learnings. "
            "Maintain a professional tone that reflects senior-level responsibility and insight. "
            "IMPORTANT: The provided statistics (hours, office days, etc.) are for your CONTEXT ONLY. "
            "Do NOT include the raw statistics in your response as they are already displayed elsewhere. "
            f"Do NOT include titles like 'Weekly Work Summary', 'Monthly Work Summary' or 'Date Range' in your response. "
            "Start directly with the summary content or the first section."
            "Instead, use them to inform your summary (e.g., if it was a fireman week, mention the impact on achievements)."
        )

        user_content = (
            f"Please create a {period} summary based on the following information:\n\n"
        )

        if stats:
            total_hours, total_minutes = TimeService.seconds_to_hours_minutes(
                stats.get("total_time_seconds", 0)
            )
            user_content += f"### {period.capitalize()} Statistics (FOR CONTEXT ONLY - DO NOT REPEAT):\n"
            user_content += f"- Total Time Worked: {total_hours}h {total_minutes}m\n"
            user_content += f"- Days at Office: {stats.get('days_at_office', 0)}\n"
            user_content += f"- Days at Home: {stats.get('days_at_home', 0)}\n"
            user_content += (
                f"- Vacation/Holiday Days: {stats.get('vacation_days', 0)}\n"
            )
            if is_fireman_week:
                user_content += (
                    "- Note: This included a **FIREMAN** week (on-call/incident response). "
                    "Make sure to highlight achievements and challenges related to being on-call.\n"
                )
            user_content += "\n"

        user_content += "### Daily Summaries:\n"
        user_content += "\n".join(f"- {s}" for s in daily_summaries)
        user_content += (
            f"\n\nProvide a brief cohesive summary first, followed by specific sections using bullet points (Key Achievements, Technical Debt, Problems Fixed, Collaboration/Mentoring, Strategic Decisions, Upcoming Focus) "
            "to structure the response and provide maximum value to stakeholders."
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content},
        ]

        payload = {
            "model": "gpt-4o-mini",  # fast & cost-effective model
            "messages": messages,
            "temperature": 0.7,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url, headers=self.headers, json=payload
                )
                response.raise_for_status()
                data = response.json()

            # Validate structure
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

        except httpx.TimeoutException:
            msg = "⚠️ The request to OpenAI timed out. Please try again."
            logger.error(msg)
            return msg
        except httpx.HTTPStatusError as e:
            msg = f"⚠️ OpenAI service error: {e.response.status_code} {e.response.reason_phrase}"
            logger.error(msg)
            return msg
        except Exception as e:
            msg = f"⚠️ Failed to summarize due to an unexpected error: {e}"
            logger.error(msg)
            return msg
