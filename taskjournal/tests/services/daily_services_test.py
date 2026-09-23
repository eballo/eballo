from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from pytest import mark, raises

from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Status, Task
from taskjournal.services.daily_audit import DailyAuditService
from taskjournal.services.daily_statistics import DailyStatisticsService
from taskjournal.services.daily_sync import DailySyncService


def test_audit_iterates_only_valid_daily_notes_but_counts_legacy_streak_files(tmp_path) -> None:
    week = tmp_path / "2025" / "week03"
    week.mkdir(parents=True)
    (week / "2025-01-15-DailyNotes.md").touch()
    (week / "invalid-DailyNotes.md").touch()
    (week / "2025-01-16-DailyNotes-Holidays.md").touch()
    legacy = tmp_path / "archive"
    legacy.mkdir()
    (legacy / "2025-01-14-OldDailyNotes.txt").touch()

    audit = DailyAuditService(MagicMock(), MagicMock(), MagicMock(), str(tmp_path), "md")

    assert list(audit.iter_daily_notes(2025)) == [
        (datetime(2025, 1, 15), str(week / "2025-01-15-DailyNotes.md"))
    ]
    assert set(audit.iter_streak_dates()) == {
        datetime(2025, 1, 14).date(),
        datetime(2025, 1, 15).date(),
        datetime(2025, 1, 16).date(),
    }


def test_statistics_uses_audit_traversal_and_keeps_completion_shape() -> None:
    parser = MagicMock()
    parser.parse.return_value = ParsedNote(planned_tasks=[
        Task(id="1", description="Done", status=Status.DONE),
        Task(id="2", description="Pending", status=Status.TODO),
    ])
    audit = MagicMock()
    audit.iter_daily_notes.return_value = iter([(datetime(2025, 1, 15), "/day.md")])

    stats = DailyStatisticsService(parser, audit)

    assert stats.get_completion_stats(2025) == [("2025-01-15", 1, 2)]
    audit.iter_daily_notes.assert_called_once_with(2025)


@mark.asyncio
async def test_sync_missing_note_does_not_call_integrations(tmp_path) -> None:
    jira = MagicMock()
    jira.get_current_sprint_tasks_all_assigned_to_me = AsyncMock()
    github = MagicMock()
    sync = DailySyncService(jira, github, MagicMock(), MagicMock(), MagicMock())

    with raises(FileNotFoundError, match="No daily notes"):
        await sync.sync_daily_notes(datetime(2025, 1, 15), str(tmp_path / "missing.md"))

    jira.get_current_sprint_tasks_all_assigned_to_me.assert_not_awaited()