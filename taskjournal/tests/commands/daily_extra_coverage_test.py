from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_mock import MockerFixture

from taskjournal.commands.commands import CommandManager
from taskjournal.models.task import Task
from taskjournal.services.utils import FormatUtils


@pytest.mark.asyncio
async def test_create_offline_monday_carries_last_week_tasks_without_integrations(
    cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
) -> None:
    monday = datetime(2025, 1, 20, 9, 0)
    path = tmp_path / "2025-01-20-DailyNotes.md"
    previous = Task(id="previous", description="Carry over")
    default = Task(id="default", description="Routine")
    mocker.patch.object(
        cmd._daily, "_get_daily_notes_file_path", return_value=str(path)
    )
    week_folder = mocker.patch.object(
        cmd._daily,
        "_get_week_folder",
        side_effect=lambda date: str(tmp_path / date.strftime("%Y-%m-%d")),
    )
    mocker.patch.object(
        cmd._daily, "get_streak_stats", return_value={"current": 0, "longest": 0}
    )
    cmd.file_service.load_template.return_value = (
        "{{ sprint_name }}|{{ tasks }}|{{ code_review_tasks }}"
    )
    cmd.task_manager.get_default_tasks.return_value = [default]
    cmd.task_manager.get_previous_pending_tasks.side_effect = [[previous], []]
    cmd.task_formatter.format_tasks.side_effect = lambda tasks, **kwargs: ",".join(
        t.description for t in tasks
    )
    cmd._daily._recurring.get_for_day = mocker.Mock(return_value=[])
    warning = mocker.patch("taskjournal.commands.daily.logger.warning")

    await cmd._daily.create_daily_notes(monday, offline=True, work_from="Home")

    cmd.jira.get_active_sprint.assert_not_called()
    cmd.jira.get_current_sprint_tasks_not_done_assigned_to_me.assert_not_called()
    cmd.github.update_status_if_task_reviewed.assert_not_called()
    warning.assert_any_call("Offline mode — skipping Jira and GitHub calls.")
    assert week_folder.call_args_list[0].args == (monday - timedelta(weeks=1),)
    assert cmd.task_manager.get_previous_pending_tasks.call_args_list[0].args == (
        str(tmp_path / "2025-01-13"),
        path.name,
    )
    cmd.task_manager.get_work_from_location.assert_not_called()
    written_path, content = cmd.file_service.write_to_file.call_args.args
    assert written_path == str(path)
    assert content.startswith("Offline mode|Routine,Carry over|")


def test_set_alarm_replaces_only_matching_tracking_file(
    cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
) -> None:
    day = datetime(2025, 1, 20)
    alarm_time = day.replace(hour=17, minute=45)
    tracking = tmp_path / ".alarm_job_2025-01-20_1745"
    tracking.write_text("old")
    mocker.patch.object(cmd._daily, "_get_week_folder", return_value=str(tmp_path))
    cancel = mocker.patch.object(cmd._daily, "_cancel_macos_alarm")
    schedule = mocker.patch.object(cmd._daily, "_schedule_macos_alarm")
    calls = mocker.Mock()
    calls.attach_mock(cancel, "cancel")
    calls.attach_mock(schedule, "schedule")

    cmd._daily.set_alarm(day, alarm_time, "Leave")

    cancel.assert_called_once_with(str(tracking))
    schedule.assert_called_once_with(alarm_time, str(tracking), "Leave")
    assert [call[0] for call in calls.mock_calls] == ["cancel", "schedule"]


def test_set_alarm_schedules_new_tracking_file_without_cancel(
    cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
) -> None:
    day = datetime(2025, 1, 20)
    alarm_time = day.replace(hour=18, minute=5)
    mocker.patch.object(cmd._daily, "_get_week_folder", return_value=str(tmp_path))
    cancel = mocker.patch.object(cmd._daily, "_cancel_macos_alarm")
    schedule = mocker.patch.object(cmd._daily, "_schedule_macos_alarm")

    cmd._daily.set_alarm(day, alarm_time)

    cancel.assert_not_called()
    schedule.assert_called_once_with(
        alarm_time, str(tmp_path / ".alarm_job_2025-01-20_1805"), "Time to wrap up!"
    )


def test_cancel_alarm_for_date_filters_tracking_files(
    cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
) -> None:
    day = datetime(2025, 1, 20)
    matching = [
        tmp_path / ".alarm_job_2025-01-20_1730",
        tmp_path / ".alarm_job_2025-01-20_1800",
    ]
    for file in matching + [
        tmp_path / ".alarm_job_2025-01-21_1800",
        tmp_path / "notes.md",
    ]:
        file.write_text("alarm")
    cmd.file_service.get_week_folder.return_value = str(tmp_path)
    cancel = mocker.patch.object(cmd._daily, "_cancel_macos_alarm")

    assert cmd._daily.cancel_alarm_for_date(day) is True

    assert {call.args[0] for call in cancel.call_args_list} == {
        str(file) for file in matching
    }
    assert cancel.call_count == 2


def test_cancel_alarm_for_date_missing_folder_returns_false(
    cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
) -> None:
    cmd.file_service.get_week_folder.return_value = str(tmp_path / "missing")
    cancel = mocker.patch.object(cmd._daily, "_cancel_macos_alarm")

    assert cmd._daily.cancel_alarm_for_date(datetime(2025, 1, 20)) is False
    cancel.assert_not_called()


@pytest.mark.asyncio
async def test_summary_provider_exception_leaves_existing_summary_untouched(
    cmd: CommandManager, mocker: MockerFixture
) -> None:
    cmd.parser.parse.return_value = SimpleNamespace(summary=["My notes"])
    cmd.ai_service.summarize_day.side_effect = RuntimeError("provider unavailable")
    warning = mocker.patch("taskjournal.commands.daily.logger.warning")
    append = mocker.patch.object(cmd._daily, "_append_ai_summary")
    fix = mocker.patch.object(cmd._daily, "fix_summary")

    await cmd._daily._generate_and_write_summary(
        "/day.md", no_summary=False, force=True
    )

    warning.assert_called_once_with("AI summary failed: provider unavailable")
    append.assert_not_called()
    fix.assert_not_called()


def test_read_breaks_seconds_ignores_invalid_values_and_sums_valid_breaks(
    cmd: CommandManager,
) -> None:
    marker = FormatUtils.wrap_with_format("Break:")

    assert (
        cmd._daily._read_breaks_seconds(
            [
                f"{marker} 00:15 lunch\n",
                f"{marker} nonsense\n",
                "Unrelated: 02:00\n",
                f"{marker} 01:05\n",
            ]
        )
        == 4800
    )


@pytest.mark.parametrize("end_line", [None, "not-a-time"])
def test_fix_time_spent_rejects_missing_or_invalid_end_time_without_writing(
    cmd: CommandManager, mocker: MockerFixture, end_line: str | None
) -> None:
    marker = FormatUtils.wrap_with_format("End Time:")
    cmd.file_service.get_lines.return_value = ["Start Time: 09:00\n"] + (
        [f"{marker} {end_line}\n"] if end_line is not None else []
    )
    cmd.time_service.get_start_time.return_value = (0, datetime(2025, 1, 20, 9))

    assert cmd._daily.fix_time_spent_from_file("/day.md") is False
    cmd.time_service.get_total_time_spent.assert_not_called()
    cmd.file_service.write_lines_to_file.assert_not_called()


def test_standup_monday_reads_friday_and_separates_task_statuses(
    cmd: CommandManager, mocker: MockerFixture
) -> None:
    monday = datetime(2025, 1, 20)
    mocker.patch.object(
        cmd._daily,
        "_get_daily_notes_file_path",
        side_effect=lambda day: f"/notes/{day:%Y-%m-%d}.md",
    )
    mocker.patch("taskjournal.commands.daily.exists", return_value=True)
    cmd.parser.parse.side_effect = [
        SimpleNamespace(
            planned_tasks=[Task(id="1", description="Friday done", status="Done")],
            code_review_tasks=[],
        ),
        SimpleNamespace(
            planned_tasks=[
                Task(id="2", description="Today todo"),
                Task(id="3", description="Blocked", status="Blocked"),
            ],
            code_review_tasks=[Task(id="4", description="Reviewed", status="Done")],
        ),
    ]

    assert cmd._daily.get_standup(monday) == {
        "done": ["Friday done"],
        "today_done": ["Reviewed"],
        "today": ["Today todo"],
        "blockers": ["Blocked"],
    }
    assert [call.args[0] for call in cmd.parser.parse.call_args_list] == [
        "/notes/2025-01-17.md",
        "/notes/2025-01-20.md",
    ]


def test_daily_statistics_and_audit_forward_to_services(
    cmd: CommandManager, mocker: MockerFixture
) -> None:
    daily = cmd._daily
    audit = daily._audit
    stats = daily._statistics
    audit.count_week_folders = mocker.Mock(return_value=42)
    audit.warn_incomplete_week_notes = mocker.Mock()
    audit.iter_daily_notes = mocker.Mock(return_value=iter(["first", "second"]))
    stats.get_completion_stats = mocker.Mock(return_value=[("week", 1, 2)])
    stats.get_workload_stats = mocker.Mock(return_value=[("week", 5)])
    stats.get_pattern_stats = mocker.Mock(return_value={"days": 5})
    stats.get_tags_stats = mocker.Mock(return_value=[("tag", 1)])
    date = datetime(2025, 1, 20)

    assert daily.count_week_folders(2025) == 42
    daily._warn_incomplete_week_notes(date, "/week")
    assert list(daily._iter_daily_notes(2025)) == ["first", "second"]
    assert daily.get_completion_stats(2025) == [("week", 1, 2)]
    assert daily.get_workload_stats(2025) == [("week", 5)]
    assert daily.get_pattern_stats(2025) == {"days": 5}
    assert daily.get_tags_stats(2025) == [("tag", 1)]
    audit.count_week_folders.assert_called_once_with(2025)
    audit.warn_incomplete_week_notes.assert_called_once_with(date, "/week")
    audit.iter_daily_notes.assert_called_once_with(2025)
    for method in (
        stats.get_completion_stats,
        stats.get_workload_stats,
        stats.get_pattern_stats,
        stats.get_tags_stats,
    ):
        method.assert_called_once_with(2025)


@pytest.mark.asyncio
async def test_sync_helpers_forward_arguments_and_return_results(
    cmd: CommandManager, mocker: MockerFixture
) -> None:
    daily = cmd._daily
    sync = daily._sync
    lines = ["## Tasks\n"]
    tasks = [Task(id="1", description="New")]
    sync._insert_missing_tasks_in_section = mocker.Mock(return_value=1)
    sync._correct_stale_task_statuses = mocker.Mock(return_value=2)
    sync._correct_existing_code_review_links = mocker.AsyncMock(return_value=3)

    assert daily._insert_missing_tasks_in_section(lines, "Planned Tasks", tasks) == 1
    assert daily._correct_stale_task_statuses(lines, tasks) == 2
    assert await daily._correct_existing_code_review_links(lines) == 3
    sync._insert_missing_tasks_in_section.assert_called_once_with(
        lines, "Planned Tasks", tasks
    )
    sync._correct_stale_task_statuses.assert_called_once_with(lines, tasks)
    sync._correct_existing_code_review_links.assert_awaited_once_with(lines)
