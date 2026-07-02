from collections.abc import Callable
from unittest.mock import MagicMock

from typer.testing import Result


class TestBackup:

    def test_backup_run_happy_path(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["backup", "run"])

        # then
        assert result.exit_code == 0
        manager_instance.create_backup.assert_called_once()

    def test_backup_schedule__installs_at_given_time(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(["backup", "schedule", "--time", "18:00"])

        assert result.exit_code == 0
        cli_manager.schedule_backup.assert_called_once_with(hour=18, minute=0)

    def test_backup_schedule__disable_removes_schedule(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(["backup", "schedule", "--disable"])

        assert result.exit_code == 0
        cli_manager.disable_backup_schedule.assert_called_once()

    def test_backup_schedule__missing_time_prints_error(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(["backup", "schedule"])

        assert result.exit_code == 0
        cli_manager.schedule_backup.assert_not_called()
        assert "--time is required" in result.output

    def test_backup_schedule__invalid_time_format_logs_error(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(["backup", "schedule", "--time", "18h00"])

        assert result.exit_code == 0
        cli_manager.schedule_backup.assert_not_called()

    def test_backup_schedule__runtime_error_logs_error(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.schedule_backup.side_effect = RuntimeError("Cannot find 'wk' binary in PATH")

        result = invoke_cli(["backup", "schedule", "--time", "09:30"])

        assert result.exit_code == 0
        cli_manager.schedule_backup.assert_called_once_with(hour=9, minute=30)
