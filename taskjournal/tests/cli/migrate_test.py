from pytest_mock import MockerFixture
from collections.abc import Callable
from unittest.mock import MagicMock

from typer.testing import Result


class TestMigrate:

    def test_migrate_daily_processes_single_file(
        self,
        cli_migration: MagicMock,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        mocker.patch(
            "taskjournal.cli.commands.migrate.isfile", return_value=True
        )
        mocker.patch(
            "taskjournal.cli.commands.migrate.isdir", return_value=False
        )

        # when
        result = invoke_cli(["migrate", "daily", "some/path.txt"])

        # then
        assert result.exit_code == 0
        cli_migration.migrate_file.assert_called_once_with("some/path.txt")
        cli_migration.migration_info.assert_called_once()

    def test_migrate_daily_scans_directory_for_legacy_files(
        self,
        cli_migration: MagicMock,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        mocker.patch(
            "taskjournal.cli.commands.migrate.isfile", return_value=False
        )
        mocker.patch(
            "taskjournal.cli.commands.migrate.isdir", return_value=True
        )
        mocker.patch(
            "taskjournal.cli.commands.migrate.walk",
            return_value=[
                ("root", [], ["2025-01-01-DailyNotes.txt", "README.md"]),
                ("root/sub", [], ["2025-01-02-DailyNotes.txt"]),
            ],
        )

        # when
        result = invoke_cli(["migrate", "daily", "some/dir"])

        # then
        assert result.exit_code == 0
        cli_migration.migrate_file.assert_any_call("root/2025-01-01-DailyNotes.txt")
        cli_migration.migrate_file.assert_any_call(
            "root/sub/2025-01-02-DailyNotes.txt"
        )
        assert cli_migration.migrate_file.call_count == 2
        cli_migration.migration_info.assert_called_once()

    def test_migrate_daily_logs_error_for_missing_path(
        self,
        cli_migration: MagicMock,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        mocker.patch(
            "taskjournal.cli.commands.migrate.isfile", return_value=False
        )
        mocker.patch(
            "taskjournal.cli.commands.migrate.isdir", return_value=False
        )
        logger = mocker.patch("taskjournal.cli.commands.migrate.logger")

        # when
        result = invoke_cli(["migrate", "daily", "missing/path"])

        # then
        assert result.exit_code == 0
        logger.error.assert_called_once_with("Path not found: missing/path")
        cli_migration.migrate_file.assert_not_called()
        cli_migration.migration_info.assert_called_once()
