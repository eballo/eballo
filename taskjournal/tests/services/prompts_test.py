from typing import Any

from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Status, Task
from taskjournal.services.ai.prompts import build_daily_prompt, build_prompt


class TestBuildDailyPrompt:

    def test_includes_done_tasks(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            planned_tasks=[Task(id="1", description="Fix bug", status=Status.DONE)],
        )
        prompt = build_daily_prompt(note)
        assert "Fix bug" in prompt
        assert "Completed" in prompt

    def test_includes_wip_tasks(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            planned_tasks=[Task(id="1", description="Review PR", status=Status.IN_PROGRESS)],
        )
        prompt = build_daily_prompt(note)
        assert "Review PR" in prompt
        assert "Work in progress" in prompt

    def test_includes_blocked_tasks(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            planned_tasks=[Task(id="1", description="Deploy", status=Status.BLOCKED)],
        )
        prompt = build_daily_prompt(note)
        assert "Deploy" in prompt
        assert "Blocked" in prompt

    def test_includes_code_review_tasks(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            code_review_tasks=[Task(id="1", description="PR-123", status=Status.TODO)],
        )
        prompt = build_daily_prompt(note)
        assert "PR-123" in prompt
        assert "Code reviews" in prompt

    def test_includes_notes_and_firefighter(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            notes=["- Attended meeting", "- Discussed roadmap"],
            firefighter=["- Incident P1"],
        )
        prompt = build_daily_prompt(note)
        assert "Attended meeting" in prompt
        assert "Incident P1" in prompt

    def test_includes_sprint_and_time_metadata(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            sprint_name="Sprint 42",
            time_spent="07:30",
            work_from="Office",
        )
        prompt = build_daily_prompt(note)
        assert "Sprint 42" in prompt
        assert "07:30" in prompt
        assert "Office" in prompt

    def test_includes_existing_summary(self) -> None:
        note = ParsedNote(date="2025-01-15", summary=["Great day overall"])
        prompt = build_daily_prompt(note)
        assert "Great day overall" in prompt
        assert "Existing summary" in prompt

    def test_skips_empty_note_lines(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            notes=["-", "---", "  "],
            firefighter=["-", "---"],
        )
        prompt = build_daily_prompt(note)
        assert "Notes:" not in prompt
        assert "Firefighter" not in prompt

    def test_code_review_status_included_in_wip(self) -> None:
        note = ParsedNote(
            date="2025-01-15",
            planned_tasks=[Task(id="1", description="Review merge", status=Status.CODE_REVIEW)],
        )
        prompt = build_daily_prompt(note)
        assert "Work in progress" in prompt


class TestBuildPrompt:

    def test_weekly_prompt_contains_daily_summaries(self) -> None:
        prompt = build_prompt(
            ["Did X", "Fixed Y"], stats=None, is_fireman_week=False, period="weekly"
        )
        assert "Did X" in prompt
        assert "Fixed Y" in prompt

    def test_prompt_includes_stats_when_provided(self) -> None:
        stats: dict[str, Any] = {
            "total_time_seconds": 3600 * 8,
            "days_at_office": 3,
            "days_at_home": 2,
            "vacation_days": 0,
        }
        prompt = build_prompt(["summary"], stats=stats, is_fireman_week=False, period="weekly")
        assert "Days at Office: 3" in prompt
        assert "Days at Home: 2" in prompt

    def test_prompt_mentions_fireman_week(self) -> None:
        stats: dict[str, Any] = {
            "total_time_seconds": 0,
            "days_at_office": 0,
            "days_at_home": 5,
            "vacation_days": 0,
        }
        prompt = build_prompt(["on-call"], stats=stats, is_fireman_week=True, period="weekly")
        assert "FIREMAN" in prompt

    def test_prompt_without_stats(self) -> None:
        prompt = build_prompt(["did work"], stats=None, is_fireman_week=False, period="monthly")
        assert "did work" in prompt
        assert "monthly" in prompt.lower()

    def test_period_label_in_prompt(self) -> None:
        prompt = build_prompt(["summary"], stats=None, is_fireman_week=False, period="quarterly")
        assert "quarterly" in prompt.lower()