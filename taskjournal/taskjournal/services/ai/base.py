from abc import abstractmethod
from typing import Any

from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus
from taskjournal.services.time import TimeService


class AIService(BaseService):
    @abstractmethod
    async def summarize(
        self,
        daily_summaries: list[str],
        stats: dict[str, Any] | None = None,
        is_fireman_week: bool = False,
        period: str = "weekly",
    ) -> str: ...


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


def build_prompt(
    daily_summaries: list[str],
    stats: dict[str, Any] | None,
    is_fireman_week: bool,
    period: str,
) -> str:
    system = (
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
        "Start directly with the summary content or the first section. "
        "Instead, use them to inform your summary (e.g., if it was a fireman week, mention the impact on achievements)."
    )

    user_content = f"Please create a {period} summary based on the following information:\n\n"

    if stats:
        total_hours, total_minutes = TimeService.seconds_to_hours_minutes(
            stats.get("total_time_seconds", 0)
        )
        user_content += f"### {period.capitalize()} Statistics (FOR CONTEXT ONLY - DO NOT REPEAT):\n"
        user_content += f"- Total Time Worked: {total_hours}h {total_minutes}m\n"
        user_content += f"- Days at Office: {stats.get('days_at_office', 0)}\n"
        user_content += f"- Days at Home: {stats.get('days_at_home', 0)}\n"
        user_content += f"- Vacation/Holiday Days: {stats.get('vacation_days', 0)}\n"
        if is_fireman_week:
            user_content += (
                "- Note: This included a **FIREMAN** week (on-call/incident response). "
                "Make sure to highlight achievements and challenges related to being on-call.\n"
            )
        user_content += "\n"

    user_content += "### Daily Summaries:\n"
    user_content += "\n".join(f"- {s}" for s in daily_summaries)
    user_content += (
        f"\n\nProvide a brief cohesive summary first, followed by specific sections using bullet points "
        "(Key Achievements, Technical Debt, Problems Fixed, Collaboration/Mentoring, Strategic Decisions, Upcoming Focus) "
        "to structure the response and provide maximum value to stakeholders."
    )

    return f"{system}\n\n{user_content}"
