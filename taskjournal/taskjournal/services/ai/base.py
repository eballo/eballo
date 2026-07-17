from abc import abstractmethod
from typing import Any

from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Status
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


def build_daily_prompt(note: ParsedNote) -> str:
    done = [t.description for t in note.planned_tasks if t.status == Status.DONE]
    wip = [t.description for t in note.planned_tasks if t.status in (Status.IN_PROGRESS, Status.CODE_REVIEW)]
    blocked = [t.description for t in note.planned_tasks if t.status == Status.BLOCKED]
    pr_reviews = [t.description for t in note.code_review_tasks]
    notes_lines = [l for l in note.notes if l.strip() and l.strip() not in ("-", "---")]
    ff_lines = [l for l in note.firefighter if l.strip() and l.strip() not in ("-", "---")]
    summary_lines = [l for l in note.summary if l.strip() and l.strip() not in ("-", "---")]

    system = (
        "You are a senior software engineer writing a brief personal daily work journal entry. "
        "Structure the entry in two parts:\n"
        "1. A short narrative summary, 3 to 8 lines, in natural English, first person, past tense. "
        "No markdown headers or bullet points in this part — just prose. "
        "Mention any blockers or unfinished work, and work location if it was the office.\n"
        "2. A bullet list titled 'Highlights:' with one short line per notable thing done that day "
        "(completed tasks, PR reviews, firefighter incidents), each on its own bullet so it reads "
        "visually rather than as a paragraph.\n"
        "Start directly with the narrative summary, no preamble. "
        "Keep the tone professional but natural — this is a personal journal, not a status report."
    )

    ctx = f"Daily journal for {note.date or 'today'}"
    if note.sprint_name:
        ctx += f", sprint: {note.sprint_name}"
    if note.time_spent:
        ctx += f", time worked: {note.time_spent}"
    if note.work_from:
        ctx += f", location: {note.work_from}"

    parts: list[str] = [ctx, ""]

    if summary_lines:
        parts.append("Existing summary notes: " + " ".join(summary_lines))
    if done:
        parts.append("Completed: " + "; ".join(done))
    if wip:
        parts.append("Work in progress: " + "; ".join(wip))
    if blocked:
        parts.append("Blocked: " + "; ".join(blocked))
    if pr_reviews:
        parts.append("Code reviews / PRs: " + "; ".join(pr_reviews))
    if notes_lines:
        parts.append("Notes: " + " ".join(notes_lines))
    if ff_lines:
        parts.append("Firefighter incidents: " + " ".join(ff_lines))

    user_content = "\n".join(parts)
    return f"{system}\n\n{user_content}"


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
