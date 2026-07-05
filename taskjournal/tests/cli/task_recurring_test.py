from collections.abc import Callable
from unittest.mock import MagicMock

from pytest import LogCaptureFixture
from typer.testing import Result


class TestTaskRecurring:

    def test_recurring_add_every_day(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(["task", "recurring", "add", "standup"])
        assert result.exit_code == 0
        cli_manager.add_recurring_task.assert_called_once_with("standup", None, False)
        assert "every day" in result.output

    def test_recurring_add_specific_days(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(["task", "recurring", "add", "sync", "--every", "monday,friday"])
        assert result.exit_code == 0
        cli_manager.add_recurring_task.assert_called_once_with("sync", ["monday", "friday"], False)
        assert "monday,friday" in result.output

    def test_recurring_add_monthly(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(["task", "recurring", "add", "Deel report", "--monthly"])
        assert result.exit_code == 0
        cli_manager.add_recurring_task.assert_called_once_with("Deel report", None, True)
        assert "first workday of each month" in result.output

    def test_recurring_add_monthly_and_every_conflict_exits(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        result = invoke_cli(["task", "recurring", "add", "x", "--monthly", "--every", "monday"])
        assert result.exit_code == 1
        assert "Cannot use --monthly" in caplog.text
        cli_manager.add_recurring_task.assert_not_called()

    def test_recurring_add_invalid_day_exits(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        result = invoke_cli(["task", "recurring", "add", "standup", "--every", "funday"])
        assert result.exit_code == 1
        assert "Unknown days" in caplog.text
        cli_manager.add_recurring_task.assert_not_called()

    def test_recurring_add_raises_value_error(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.add_recurring_task.side_effect = ValueError("bad day")
        result = invoke_cli(["task", "recurring", "add", "standup"])
        assert result.exit_code == 1
        assert "bad day" in caplog.text
        cli_manager.add_recurring_task.assert_called_once_with("standup", None, False)

    def test_recurring_list_shows_tasks(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_recurring_tasks.return_value = [
            {"description": "standup", "days": "every"},
            {"description": "sync", "days": ["monday", "friday"]},
            {"description": "Deel report", "days": "monthly_first_workday"},
        ]
        result = invoke_cli(["task", "recurring", "list"])
        assert result.exit_code == 0
        assert "standup" in result.output
        assert "sync" in result.output
        assert "first workday of each month" in result.output

    def test_recurring_list_shows_empty_message(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_recurring_tasks.return_value = []
        result = invoke_cli(["task", "recurring", "list"])
        assert result.exit_code == 0
        assert "No recurring tasks" in result.output

    def test_recurring_remove_found(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.remove_recurring_task.return_value = True
        result = invoke_cli(["task", "recurring", "remove", "standup"])
        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_recurring_remove_not_found_exits(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.remove_recurring_task.return_value = False
        result = invoke_cli(["task", "recurring", "remove", "nonexistent"])
        assert result.exit_code == 1
        assert "No recurring task found" in caplog.text
