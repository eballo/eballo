from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

from pytest_mock import MockerFixture
from typer.testing import Result


class TestBackup:

    def test_verify_valid_archive(
        self, cli_manager: MagicMock, invoke_cli: Callable[[list[str]], Result]
    ) -> None:
        cli_manager.inspect_backup.return_value = [
            (Path("old.txt"), True),
            (Path("new.md"), False),
        ]

        result = invoke_cli(["backup", "verify", "saved.zip"])

        assert result.exit_code == 0
        assert "2 files" in result.output
        cli_manager.inspect_backup.assert_called_once_with(Path("saved.zip"))

    def test_verify_invalid_archive_exits_nonzero(
        self, cli_manager: MagicMock, invoke_cli: Callable[[list[str]], Result]
    ) -> None:
        cli_manager.inspect_backup.side_effect = ValueError("Unsafe backup entry")

        result = invoke_cli(["backup", "verify", "saved.zip"])

        assert result.exit_code == 1
        assert "Unsafe backup entry" in result.output

    def test_restore_previews_and_requires_confirmation(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
    ) -> None:
        cli_manager.inspect_backup.return_value = [
            (Path("old.txt"), True),
            (Path("new.md"), False),
        ]
        confirmation = mocker.patch(
            "taskjournal.cli.commands.backup.confirm", return_value=False
        )

        result = invoke_cli(["backup", "restore", "saved.zip"])

        assert result.exit_code == 0
        assert "Skip (exists): old.txt" in result.output
        assert "Restore: new.md" in result.output
        assert "Restore cancelled" in result.output
        confirmation.assert_called_once()
        cli_manager.restore_backup.assert_not_called()

    def test_restore_confirmed_restores_only_missing(
        self, cli_manager: MagicMock, invoke_cli: Callable[[list[str]], Result]
    ) -> None:
        cli_manager.inspect_backup.return_value = [
            (Path("old.txt"), True),
            (Path("new.md"), False),
        ]
        cli_manager.restore_backup.return_value = [Path("new.md")]

        result = invoke_cli(["backup", "restore", "saved.zip", "--yes"])

        assert result.exit_code == 0
        assert "Restored 1 files" in result.output
        cli_manager.restore_backup.assert_called_once_with(Path("saved.zip"))

    def test_restore_with_no_missing_files_does_not_call_service(
        self, cli_manager: MagicMock, invoke_cli: Callable[[list[str]], Result]
    ) -> None:
        cli_manager.inspect_backup.return_value = [(Path("old.txt"), True)]

        result = invoke_cli(["backup", "restore", "saved.zip", "--yes"])

        assert result.exit_code == 0
        cli_manager.restore_backup.assert_not_called()

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
        cli_manager.schedule_backup.side_effect = RuntimeError(
            "Cannot find 'wk' binary in PATH"
        )

        result = invoke_cli(["backup", "schedule", "--time", "09:30"])

        assert result.exit_code == 0
        cli_manager.schedule_backup.assert_called_once_with(hour=9, minute=30)
