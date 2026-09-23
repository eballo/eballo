from collections.abc import Callable
from datetime import datetime
from unittest.mock import MagicMock, call

from freezegun import freeze_time
from pytest import LogCaptureFixture, mark
from pytest_mock import MockerFixture
from typer.testing import Result


@mark.parametrize(
    ("reply", "expected_end", "message"),
    [
        (
            "17:30",
            datetime(2026, 1, 18, 17, 30),
            "End time set and time spent calculated",
        ),
        ("not-a-time", None, "Invalid format (expected HH:MM)"),
        ("", None, None),
    ],
)
@freeze_time("2026-01-19 09:00:00")
def test_start_repairs_previous_day_missing_end_time(
    reply: str,
    expected_end: datetime | None,
    message: str | None,
    mocker: MockerFixture,
    cli_manager: MagicMock,
    invoke_cli: Callable[[list[str]], Result],
) -> None:
    cli_manager.create_daily_notes = mocker.AsyncMock()
    cli_manager.get_previous_day_issues.return_value = (
        "2026-01-18",
        "/previous.md",
        ["missing end time"],
    )
    answers = mocker.patch("builtins.input", side_effect=[" Y ", reply])

    result = invoke_cli(["daily", "start", "--offline"])

    assert result.exit_code == 0, result.output
    assert answers.call_count == 2
    if expected_end:
        cli_manager.fix_end_time_and_time_spent.assert_called_once_with(
            "/previous.md", expected_end
        )
    else:
        cli_manager.fix_end_time_and_time_spent.assert_not_called()
    if message:
        assert message in result.output
    cli_manager.create_daily_notes.assert_awaited_once_with(
        datetime(2026, 1, 19, 9), False, False, None, True, energy=None
    )


@freeze_time("2026-01-19 09:00:00")
def test_start_reports_rejected_previous_day_end_time_and_saves_summary(
    mocker: MockerFixture,
    cli_manager: MagicMock,
    invoke_cli: Callable[[list[str]], Result],
) -> None:
    cli_manager.create_daily_notes = mocker.AsyncMock()
    cli_manager.get_previous_day_issues.return_value = (
        "2026-01-18",
        "/previous.md",
        ["missing end time", "missing summary"],
    )
    cli_manager.fix_end_time_and_time_spent.side_effect = ValueError("end before start")
    mocker.patch(
        "builtins.input", side_effect=["y", "08:00", "  Finished the report  "]
    )

    result = invoke_cli(["daily", "start", "--offline"])

    assert result.exit_code == 0, result.output
    cli_manager.fix_end_time_and_time_spent.assert_called_once_with(
        "/previous.md", datetime(2026, 1, 18, 8)
    )
    cli_manager.fix_summary.assert_called_once_with(
        "/previous.md", "Finished the report"
    )
    assert "end before start" in result.output
    assert "Summary saved" in result.output


@mark.parametrize(
    ("computed", "reply", "expected_end", "message"),
    [
        (True, None, None, "Time spent calculated from existing times"),
        (
            False,
            "18:15",
            datetime(2026, 1, 18, 18, 15),
            "End time set and time spent calculated",
        ),
        (False, "bad", None, "Invalid format (expected HH:MM)"),
        (False, "", None, None),
    ],
)
@freeze_time("2026-01-19 09:00:00")
def test_start_repairs_previous_day_missing_time_spent(
    computed: bool,
    reply: str | None,
    expected_end: datetime | None,
    message: str | None,
    mocker: MockerFixture,
    cli_manager: MagicMock,
    invoke_cli: Callable[[list[str]], Result],
) -> None:
    cli_manager.create_daily_notes = mocker.AsyncMock()
    cli_manager.get_previous_day_issues.return_value = (
        "2026-01-18",
        "/previous.md",
        ["missing time spent", "missing summary"],
    )
    cli_manager.fix_time_spent_from_file.return_value = computed
    responses = ["y", "  "] if computed else ["y", reply, "  "]
    answers = mocker.patch("builtins.input", side_effect=responses)

    result = invoke_cli(["daily", "start", "--offline"])

    assert result.exit_code == 0, result.output
    assert answers.call_count == len(responses)
    cli_manager.fix_time_spent_from_file.assert_called_once_with("/previous.md")
    cli_manager.fix_summary.assert_not_called()
    if expected_end:
        cli_manager.fix_end_time_and_time_spent.assert_called_once_with(
            "/previous.md", expected_end
        )
    else:
        cli_manager.fix_end_time_and_time_spent.assert_not_called()
    if message:
        assert message in result.output


@freeze_time("2026-01-19 09:00:00")
def test_start_continues_after_time_spent_fallback_rejects_end_time(
    mocker: MockerFixture,
    cli_manager: MagicMock,
    invoke_cli: Callable[[list[str]], Result],
) -> None:
    cli_manager.create_daily_notes = mocker.AsyncMock()
    cli_manager.get_previous_day_issues.return_value = (
        "2026-01-18",
        "/previous.md",
        ["missing time spent"],
    )
    cli_manager.fix_time_spent_from_file.return_value = False
    cli_manager.fix_end_time_and_time_spent.side_effect = ValueError("end before start")
    mocker.patch("builtins.input", side_effect=["y", "08:00"])

    result = invoke_cli(["daily", "start", "--offline"])

    assert result.exit_code == 0, result.output
    cli_manager.fix_end_time_and_time_spent.assert_called_once_with(
        "/previous.md", datetime(2026, 1, 18, 8)
    )
    assert "end before start" in result.output
    cli_manager.create_daily_notes.assert_awaited_once()


@freeze_time("2026-01-19 09:00:00")
def test_start_declines_previous_day_repairs(
    mocker: MockerFixture,
    cli_manager: MagicMock,
    invoke_cli: Callable[[list[str]], Result],
    caplog: LogCaptureFixture,
) -> None:
    cli_manager.create_daily_notes = mocker.AsyncMock()
    cli_manager.get_previous_day_issues.return_value = (
        "2026-01-18",
        "/previous.md",
        ["missing summary"],
    )
    answers = mocker.patch("builtins.input", return_value="n")

    result = invoke_cli(["daily", "start", "--offline"])

    assert result.exit_code == 0, result.output
    answers.assert_called_once_with("Fix it now? [y/N]: ")
    assert "2026-01-18" in caplog.text
    cli_manager.fix_summary.assert_not_called()
    cli_manager.create_daily_notes.assert_awaited_once()


@mark.parametrize(
    ("choice", "location", "expected_calls"),
    [
        (
            "Office",
            "Office",
            [
                call(
                    "Working from?", choices=["Home", "Office", "Other"], default="Home"
                )
            ],
        ),
        (
            "Other",
            "Cafe",
            [
                call(
                    "Working from?", choices=["Home", "Office", "Other"], default="Home"
                ),
                call("Enter your location"),
            ],
        ),
    ],
)
@freeze_time("2026-01-19 09:00:00")
def test_start_prompts_for_unknown_wifi_location(
    choice: str,
    location: str,
    expected_calls: list,
    mocker: MockerFixture,
    cli_manager: MagicMock,
    invoke_cli: Callable[[list[str]], Result],
) -> None:
    cli_manager.create_daily_notes = mocker.AsyncMock()
    cli_manager.get_wifi_location.return_value = None
    prompt = mocker.patch(
        "taskjournal.cli.commands.daily.Prompt.ask",
        side_effect=[choice, location] if choice == "Other" else [choice],
    )

    result = invoke_cli(["daily", "start"])

    assert result.exit_code == 0, result.output
    assert prompt.call_args_list == expected_calls
    cli_manager.create_daily_notes.assert_awaited_once_with(
        datetime(2026, 1, 19, 9), False, False, location, False, energy=None
    )


@mark.parametrize(
    ("options", "location", "offline"),
    [(["--offline"], None, True), (["--w", "Home"], "Home", False)],
)
@freeze_time("2026-01-19 09:00:00")
def test_start_skips_location_prompt_when_unnecessary(
    options: list[str],
    location: str | None,
    offline: bool,
    mocker: MockerFixture,
    cli_manager: MagicMock,
    invoke_cli: Callable[[list[str]], Result],
) -> None:
    cli_manager.create_daily_notes = mocker.AsyncMock()
    cli_manager.get_wifi_location.return_value = None
    prompt = mocker.patch("taskjournal.cli.commands.daily.Prompt.ask")

    result = invoke_cli(["daily", "start", *options])

    assert result.exit_code == 0, result.output
    prompt.assert_not_called()
    cli_manager.get_wifi_location.assert_not_called()
    cli_manager.create_daily_notes.assert_awaited_once_with(
        datetime(2026, 1, 19, 9), False, False, location, offline, energy=None
    )


@mark.parametrize("command", ["status", "check"])
@freeze_time("2026-01-19 09:00:00")
def test_daily_missing_file_exits_before_reading_note(
    command: str,
    mocker: MockerFixture,
    cli_manager: MagicMock,
    invoke_cli: Callable[[list[str]], Result],
    caplog: LogCaptureFixture,
) -> None:
    resolve = mocker.patch(
        "taskjournal.cli.commands.daily.TimeService.resolve_daily_notes_file",
        return_value=("/missing.md", "/week"),
    )
    exists = mocker.patch("taskjournal.cli.commands.daily.exists", return_value=False)
    read_lines = mocker.patch("taskjournal.cli.commands.daily.FileService.get_lines")
    calculate = mocker.patch(
        "taskjournal.cli.commands.daily.TimeService.calculate_working_hours"
    )

    result = invoke_cli(["daily", command, "--date", "2026-01-18"])

    assert result.exit_code == 1
    assert "No daily notes found for 2026-01-18." in caplog.text
    resolve.assert_called_once_with(datetime(2026, 1, 18))
    exists.assert_called_once_with("/missing.md")
    read_lines.assert_not_called()
    calculate.assert_not_called()
    cli_manager.parser.parse.assert_not_called()
