from collections.abc import Callable
from datetime import datetime
from unittest.mock import MagicMock

from pytest import LogCaptureFixture, mark
from pytest_mock import MockerFixture
from typer.testing import Result

from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Status, Task


@mark.parametrize(
    ("start_present", "finalized", "tasks_present", "summary_present", "issue_count"),
    [
        (True, True, True, True, 0),
        (False, True, True, True, 1),
        (True, False, True, True, 1),
        (True, True, False, True, 1),
        (True, True, True, False, 1),
        (False, False, False, False, 4),
    ],
)
def test_daily_check_exit_matches_issues(
    cli_manager: MagicMock,
    invoke_cli: Callable[[list[str]], Result],
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
    start_present: bool,
    finalized: bool,
    tasks_present: bool,
    summary_present: bool,
    issue_count: int,
) -> None:
    mocker.patch(
        "taskjournal.cli.commands.daily.TimeService.resolve_daily_notes_file",
        return_value=("/day.md", "/week"),
    )
    mocker.patch("taskjournal.cli.commands.daily.exists", return_value=True)
    mocker.patch(
        "taskjournal.cli.commands.daily.FileService.get_lines", return_value=["line\n"]
    )
    start = mocker.patch(
        "taskjournal.cli.commands.daily.TimeService.get_start_time",
        return_value=(0, datetime(2026, 1, 19, 9, 0)),
    )
    if not start_present:
        start.side_effect = ValueError("missing start time")
    mocker.patch(
        "taskjournal.cli.commands.daily.FileService.check_finalized_in_file",
        return_value=finalized,
    )
    cli_manager.parser.parse.return_value = ParsedNote(
        planned_tasks=(
            [Task(id="1", description="Done", status=Status.DONE)]
            if tasks_present
            else []
        ),
        summary=["Summary"] if summary_present else [],
    )

    result = invoke_cli(["daily", "check", "--date", "2026-01-19"])

    assert result.exit_code == (1 if issue_count else 0)
    assert "Start time" in result.output
    assert "End time" in result.output
    assert "Tasks" in result.output
    assert "Summary" in result.output
    if issue_count:
        assert (
            f"{issue_count} issue{'s' if issue_count > 1 else ''} found." in caplog.text
        )
    else:
        assert "All checks passed." in result.output


def test_daily_check_missing_file_still_fails(
    invoke_cli: Callable[[list[str]], Result],
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
) -> None:
    mocker.patch(
        "taskjournal.cli.commands.daily.TimeService.resolve_daily_notes_file",
        return_value=("/missing.md", "/week"),
    )
    mocker.patch("taskjournal.cli.commands.daily.exists", return_value=False)

    result = invoke_cli(["daily", "check", "--date", "2026-01-19"])

    assert result.exit_code == 1
    assert "Daily check" in result.output
    assert "No daily notes found for 2026-01-19." in caplog.text
