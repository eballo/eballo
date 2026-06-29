from asyncio import create_subprocess_exec, wait_for
from asyncio import subprocess as aio_subprocess
from shutil import which
from typing import Any

from taskjournal.services.ai_service import AIService
from taskjournal.services.base import HealthCheckResult, ServiceStatus
from taskjournal.services.logger import logger
from taskjournal.services.time import TimeService


class ClaudeCodeService(AIService):
    @property
    def name(self) -> str:
        return "Claude Code"

    def health_check(self) -> HealthCheckResult:
        if which("claude") is None:
            return HealthCheckResult(
                ServiceStatus.UNCONFIGURED,
                "claude CLI not found — install Claude Code to enable AI summaries",
            )
        return HealthCheckResult(ServiceStatus.OK, "claude CLI available")

    async def summarize(
        self,
        daily_summaries: list[str],
        stats: dict[str, Any] | None = None,
        is_fireman_week: bool = False,
        period: str = "weekly",
    ) -> str:
        if not daily_summaries:
            return "No summaries provided."

        prompt = _build_prompt(daily_summaries, stats, is_fireman_week, period)

        try:
            proc = await create_subprocess_exec(
                "claude",
                "-p",
                prompt,
                stdout=aio_subprocess.PIPE,
                stderr=aio_subprocess.PIPE,
            )
            stdout, stderr = await wait_for(proc.communicate(), timeout=120.0)
            if proc.returncode != 0:
                err = stderr.decode().strip()
                msg = f"⚠️ Claude Code returned exit code {proc.returncode}: {err}"
                logger.error(msg)
                return msg
            return stdout.decode().strip()
        except TimeoutError:
            msg = "⚠️ The request to Claude Code timed out. Please try again."
            logger.error(msg)
            return msg
        except Exception as e:
            msg = f"⚠️ Failed to summarize due to an unexpected error: {e}"
            logger.error(msg)
            return msg


def _build_prompt(
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
