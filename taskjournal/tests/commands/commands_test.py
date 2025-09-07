from __future__ import annotations

import os
from datetime import datetime, timedelta
from types import SimpleNamespace

from pytest import fixture
from pytest_mock import MockerFixture

from taskjournal.commands.commands import CommandManager
from taskjournal.models.task import Status


# ----------------------------
# Fixtures
# ----------------------------


@fixture
def fixed_datetime() -> datetime:
    return datetime(2025, 1, 15, 9, 30, 0)


@fixture
def cmd(mocker: MockerFixture) -> CommandManager:
    mocker.patch(
        "taskjournal.commands.commands.JiraService",
        return_value=mocker.MagicMock(name="JiraServiceMock"),
    )
    mocker.patch(
        "taskjournal.commands.commands.GithubService",
        return_value=mocker.MagicMock(name="GithubServiceMock"),
    )
    mocker.patch(
        "taskjournal.commands.commands.FileWriter",
        return_value=mocker.MagicMock(name="FileWriterMock"),
    )

    cm = CommandManager()
    return cm


@fixture
def temp_week_folder(tmp_path) -> str:
    return str(tmp_path / "week3")


# ----------------------------
# _get_week_folder
# ----------------------------


def test__get_week_folder__creates_dir_and_returns_path(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    get_week_folder = mocker.patch(
        "taskjournal.commands.commands.get_week_folder", return_value=temp_week_folder
    )
    makedirs = mocker.patch("taskjournal.commands.commands.os.makedirs")

    # when
    result = cmd._get_week_folder(fixed_datetime)

    # then
    assert result == temp_week_folder
    get_week_folder.assert_called_once()
    makedirs.assert_called_once_with(temp_week_folder, exist_ok=True)


# ----------------------------
# _get_daily_notes_file_path
# ----------------------------


def test__get_daily_notes_file_path__joins_week_folder_and_filename(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    mocker.patch.object(cmd, "_get_week_folder", return_value=temp_week_folder)
    get_daily_notes_name = mocker.patch(
        "taskjournal.commands.commands.get_daily_notes_name",
        return_value="2025-01-15-DailyNotes.md",
    )

    # when
    path = cmd._get_daily_notes_file_path(fixed_datetime)

    # then
    assert path.endswith(os.path.join("week3", "2025-01-15-DailyNotes.md"))
    get_daily_notes_name.assert_called_once_with(fixed_datetime)


# ----------------------------
# create_daily_notes
# ----------------------------


def test_create_daily_notes__skips_when_file_exists_and_not_forced(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    mocker.patch.object(
        cmd,
        "_get_daily_notes_file_path",
        return_value=os.path.join(temp_week_folder, "2025-01-15-DailyNotes.md"),
    )
    mocker.patch(
        "taskjournal.commands.commands.load_template",
        return_value="date={{date}}, time={{time}}, sprint={{sprint_name}}",
    )
    mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=True)
    warn = mocker.patch("taskjournal.commands.commands.logger.warning")

    # when
    cmd.create_daily_notes(fixed_datetime, force=False)

    # then
    warn.assert_called_once()
    cmd.file_writer.format_content.assert_not_called()


def test_create_daily_notes__creates_when_forced_even_if_exists(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    path = os.path.join(temp_week_folder, "2025-01-15-DailyNotes.md")
    mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value=path)
    mocker.patch(
        "taskjournal.commands.commands.load_template",
        return_value="date={{date}}, time={{time}}, sprint={{sprint_name}}\n{{tasks}}\n{{code_review_tasks}}",
    )
    mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=True)
    mocker.patch(
        "taskjournal.commands.commands.get_default_tasks", return_value=["task-default"]
    )
    mocker.patch.object(
        cmd.jira,
        "get_current_sprint_tasks_not_done_assigned_to_me",
        return_value=["task-jira-pending"],
    )
    mocker.patch.object(
        cmd.jira,
        "get_current_sprint_tasks_in_code_review",
        return_value=["task-code-review"],
    )
    mocker.patch(
        "taskjournal.commands.commands.get_previous_pending_tasks",
        return_value=["task-prev"],
    )
    mocker.patch(
        "taskjournal.commands.commands.unique_tasks",
        return_value=["task-default", "task-prev", "task-jira-pending"],
    )
    write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")
    # Use SimpleNamespace to provide a .name attribute without conflicting with MagicMock's 'name' kwarg
    mocker.patch.object(
        cmd.jira, "get_active_sprint", return_value=SimpleNamespace(name="Sprint 42")
    )
    info = mocker.patch("taskjournal.commands.commands.logger.info")

    # when
    cmd.create_daily_notes(fixed_datetime, force=True)

    # then
    write_to_file.assert_called_once()
    assert cmd.file_writer.format_content.call_count == 2
    assert any(
        "Estimated time to finish" in " ".join(map(str, c.args))
        for c in info.mock_calls
    )


def test_create_daily_notes__uses_fallback_sprint_name_when_no_active_sprint(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    mocker.patch.object(
        cmd,
        "_get_daily_notes_file_path",
        return_value=os.path.join(temp_week_folder, "2025-01-15-DailyNotes.md"),
    )
    mocker.patch(
        "taskjournal.commands.commands.load_template",
        return_value="sprint={{sprint_name}}\n{{tasks}}\n{{code_review_tasks}}",
    )
    mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=False)
    mocker.patch.object(cmd.jira, "get_active_sprint", return_value=None)
    mocker.patch("taskjournal.commands.commands.get_default_tasks", return_value=[])
    mocker.patch.object(
        cmd.jira, "get_current_sprint_tasks_not_done_assigned_to_me", return_value=[]
    )
    mocker.patch.object(
        cmd.jira, "get_current_sprint_tasks_in_code_review", return_value=[]
    )
    mocker.patch(
        "taskjournal.commands.commands.get_previous_pending_tasks", return_value=[]
    )
    mocker.patch("taskjournal.commands.commands.unique_tasks", return_value=[])
    write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")

    # Make FileWriter.format_content a pass-through so it returns the current content string
    cmd.file_writer.format_content.side_effect = (
        lambda marker, content, *_args, **_kwargs: content
    )

    # when
    cmd.create_daily_notes(fixed_datetime)

    # then
    args, _ = write_to_file.call_args
    content: str = args[1]
    assert "No active sprint" in content


# ----------------------------
# finalize_daily_notes
# ----------------------------


def test_finalize_daily_notes__errors_when_file_missing(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    mocker.patch.object(
        cmd,
        "_get_daily_notes_file_path",
        return_value=os.path.join(temp_week_folder, "missing.md"),
    )
    mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=False)
    err = mocker.patch("taskjournal.commands.commands.logger.error")

    # when
    cmd.finalize_daily_notes(fixed_datetime)

    # then
    err.assert_called_once()


def test_finalize_daily_notes__writes_end_and_spent_time_with_custom_date(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    path = os.path.join(temp_week_folder, "2025-01-15-DailyNotes.md")
    mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value=path)
    mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=True)
    mocker.patch(
        "taskjournal.commands.commands.check_finalized_in_file", return_value=False
    )
    content = ["## 2025-01-15 09:30\n", "Other line\n"]
    mocker.patch("taskjournal.commands.commands.get_lines", return_value=list(content))
    mocker.patch(
        "taskjournal.commands.commands.get_start_time", return_value=(0, fixed_datetime)
    )
    wrap = mocker.patch(
        "taskjournal.commands.commands.wrap_with_format",
        side_effect=lambda s: f"**{s}**",
    )
    write_lines = mocker.patch("taskjournal.commands.commands.write_lines_to_file")
    info = mocker.patch("taskjournal.commands.commands.logger.info")
    custom_end = fixed_datetime + timedelta(hours=2, minutes=15)

    # when
    cmd.finalize_daily_notes(custom_end)

    # then
    write_lines.assert_called_once()
    assert wrap.call_count >= 2
    assert any(
        "Total Time Spent: 02:15" in " ".join(map(str, c.args)) for c in info.mock_calls
    )


def test_finalize_daily_notes__uses_now_when_no_custom_date(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    path = os.path.join(temp_week_folder, "2025-01-15-DailyNotes.md")
    mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value=path)
    mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=True)
    mocker.patch(
        "taskjournal.commands.commands.check_finalized_in_file", return_value=False
    )
    mocker.patch("taskjournal.commands.commands.get_lines", return_value=["start\n"])
    mocker.patch(
        "taskjournal.commands.commands.get_start_time", return_value=(0, fixed_datetime)
    )
    mocker.patch(
        "taskjournal.commands.commands.wrap_with_format", side_effect=lambda s: f"[{s}]"
    )
    mocker.patch("taskjournal.commands.commands.write_lines_to_file")
    # Assumption: patch datetime.now via module-level reference
    mocker.patch(
        "taskjournal.commands.commands.datetime",
        **{
            "now.return_value": fixed_datetime + timedelta(hours=1),
            "strftime": datetime.strftime,
        },
    )

    # when
    cmd.finalize_daily_notes(custom_date=None)  # type: ignore[arg-type]

    # then
    assert True


# ----------------------------
# daily_time
# ----------------------------


def test_daily_time__calculates_when_file_exists(
    cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
) -> None:
    # given
    path = "/tmp/week3/2025-01-15-DailyNotes.md"
    mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value=path)
    mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=True)
    calc = mocker.patch.object(cmd, "_calculate_time")

    # when
    cmd.daily_time(fixed_datetime)

    # then
    calc.assert_called_once_with(path)


def test_daily_time__warns_when_missing(
    cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
) -> None:
    # given
    mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value="/missing.md")
    mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=False)
    warn = mocker.patch("taskjournal.commands.commands.logger.warning")

    # when
    cmd.daily_time(fixed_datetime)

    # then
    warn.assert_called_once()


# ----------------------------
# create_week_summary
# ----------------------------


def test_create_week_summary__aggregates_done_pending_and_total_time(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    mocker.patch.object(cmd, "_get_week_folder", return_value=temp_week_folder)
    mocker.patch(
        "taskjournal.commands.commands.load_template",
        return_value="t={{total_time}}\ndone={{done_tasks}}\npending={{pending_tasks}}\n{{summary}}",
    )
    files = ["2025-01-13-DailyNotes.md", "2025-01-14-DailyNotes.md", "notes.txt"]
    mocker.patch("taskjournal.commands.commands.os.listdir", return_value=files)

    # Simulate tasks extracted from daily notes
    Task = type(
        "Task",
        (),
        {"__str__": lambda self: getattr(self, "name"), "status": Status.DONE},
    )
    todo_task = Task()
    setattr(todo_task, "name", "TODO-1")
    setattr(todo_task, "status", Status.TODO)
    done_task = Task()
    setattr(done_task, "name", "DONE-1")
    setattr(done_task, "status", Status.DONE)
    get_tasks = mocker.patch(
        "taskjournal.commands.commands.get_tasks_from_daily_notes",
        side_effect=[[done_task, todo_task], [done_task]],
    )
    mocker.patch(
        "taskjournal.commands.commands.get_total_time_from_daily_notes",
        side_effect=[3600, 1800],
    )
    write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")

    # when
    cmd.create_week_summary(fixed_datetime)

    # then
    assert get_tasks.call_count == 2
    args, _ = write_to_file.call_args
    content: str = args[1]
    assert " 1 hours and 30 minutes" in content
    assert "DONE-1" in content
    assert "TODO-1" in content


# ----------------------------
# create_half_year_review
# ----------------------------


def test_create_half_year_review__writes_counts_and_lists(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    mocker.patch.object(cmd, "_get_week_folder", return_value=temp_week_folder)
    mocker.patch(
        "taskjournal.commands.commands.load_template",
        return_value="tasks={{total_tasks}}, epics={{total_epics}}, gh={{github_contributions}}\n{{tasks}}\n{{epics}}",
    )
    tasks = ["T-1", "T-2", "T-3"]
    mocker.patch.object(
        cmd.jira, "get_current_tasks_assigned_to_me_last_6_months", return_value=tasks
    )
    mocker.patch(
        "taskjournal.commands.commands.get_unique_epics", return_value=["E-1", "E-2"]
    )
    mocker.patch.object(cmd.github, "get_contributions_last_6_months", return_value=123)
    write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")

    # when
    cmd.create_half_year_review(fixed_datetime)

    # then
    content: str = write_to_file.call_args[0][1]
    assert "tasks=3" in content and "epics=2" in content and "gh=123" in content


# ----------------------------
# create_month_review
# ----------------------------


def test_create_month_review__writes_counts_and_lists(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    mocker.patch.object(cmd, "_get_week_folder", return_value=temp_week_folder)
    mocker.patch(
        "taskjournal.commands.commands.load_template",
        return_value="tasks={{total_tasks}}, epics={{total_epics}}, gh={{github_contributions}}",
    )
    mocker.patch.object(
        cmd.jira, "get_current_tasks_assigned_to_me_last_month", return_value=["M-1"]
    )
    mocker.patch(
        "taskjournal.commands.commands.get_unique_epics", return_value=["ME-1"]
    )
    mocker.patch.object(cmd.github, "get_contributions_last_month", return_value=7)
    write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")

    # when
    cmd.create_month_review(fixed_datetime)

    # then
    content: str = write_to_file.call_args[0][1]
    assert "tasks=1" in content and "epics=1" in content and "gh=7" in content


# ----------------------------
# create_retro
# ----------------------------


def test_create_retro__creates_when_missing_and_injects_sprint_name(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    mocker.patch.object(cmd, "_get_week_folder", return_value=temp_week_folder)
    mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=False)
    mocker.patch(
        "taskjournal.commands.commands.load_template",
        return_value="retro {{sprint_name}}",
    )
    # Use SimpleNamespace here too to avoid MagicMock 'name' kwarg conflict
    mocker.patch.object(
        cmd.jira, "get_active_sprint", return_value=SimpleNamespace(name="Alpha")
    )
    write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")

    # when
    cmd.create_retro(fixed_datetime)

    # then
    content: str = write_to_file.call_args[0][1]
    assert "Alpha" in content


def test_create_retro__noop_when_file_exists(
    cmd: CommandManager,
    mocker: MockerFixture,
    fixed_datetime: datetime,
    temp_week_folder: str,
) -> None:
    # given
    mocker.patch.object(cmd, "_get_week_folder", return_value=temp_week_folder)
    mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=True)
    write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")

    # when
    cmd.create_retro(fixed_datetime)

    # then
    write_to_file.assert_not_called()


# ----------------------------
# create_backup
# ----------------------------


def test_create_backup__logs_backup_path(
    cmd: CommandManager, mocker: MockerFixture
) -> None:
    # given
    mocker.patch(
        "taskjournal.commands.commands.create_backup", return_value="/tmp/backup.zip"
    )
    info = mocker.patch("taskjournal.commands.commands.logger.info")

    # when
    cmd.create_backup()

    # then
    assert any(
        "Backup created at: /tmp/backup.zip" in " ".join(map(str, c.args))
        for c in info.mock_calls
    )


# ----------------------------
# _calculate_time
# ----------------------------


def test__calculate_time__logs_when_elapsed_available(
    cmd: CommandManager, mocker: MockerFixture
) -> None:
    # given
    mocker.patch(
        "taskjournal.commands.commands.calculate_working_hours",
        return_value=("09:00", 3.5, datetime(2025, 1, 15, 12, 30)),
    )
    info = mocker.patch("taskjournal.commands.commands.logger.info")

    # when
    cmd._calculate_time("/tmp/day.md")

    # then
    assert info.call_count == 3


def test__calculate_time__logs_error_when_elapsed_missing(
    cmd: CommandManager, mocker: MockerFixture
) -> None:
    # given
    mocker.patch(
        "taskjournal.commands.commands.calculate_working_hours",
        return_value=(None, None, None),
    )
    err = mocker.patch("taskjournal.commands.commands.logger.error")

    # when
    cmd._calculate_time("/tmp/day.md")

    # then
    err.assert_called_once()
