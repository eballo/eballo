from pytest_mock import MockerFixture
from collections.abc import Callable

from typer.testing import Result


class TestMigrate:

    def test_migrate_daily_processes_single_file(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        service_instance = mocker.MagicMock()
        service_cls = mocker.patch(
            "taskjournal.cli.commands.migrate.MigrationService",
            return_value=service_instance,
        )
        mocker.patch(
            "taskjournal.cli.commands.migrate.os.path.isfile", return_value=True
        )
        mocker.patch(
            "taskjournal.cli.commands.migrate.os.path.isdir", return_value=False
        )

        # when
        result = invoke_cli(["migrate", "daily", "some/path.txt"])

        # then
        assert result.exit_code == 0
        service_cls.assert_called_once()
        service_instance.migrate_file.assert_called_once_with("some/path.txt")
        service_instance.migration_info.assert_called_once()

    def test_migrate_daily_scans_directory_for_legacy_files(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        service_instance = mocker.MagicMock()
        mocker.patch(
            "taskjournal.cli.commands.migrate.MigrationService",
            return_value=service_instance,
        )
        mocker.patch(
            "taskjournal.cli.commands.migrate.os.path.isfile", return_value=False
        )
        mocker.patch(
            "taskjournal.cli.commands.migrate.os.path.isdir", return_value=True
        )
        mocker.patch(
            "taskjournal.cli.commands.migrate.os.walk",
            return_value=[
                ("root", [], ["2025-01-01-DailyNotes.txt", "README.md"]),
                ("root/sub", [], ["2025-01-02-DailyNotes.txt"]),
            ],
        )

        # when
        result = invoke_cli(["migrate", "daily", "some/dir"])

        # then
        assert result.exit_code == 0
        service_instance.migrate_file.assert_any_call("root/2025-01-01-DailyNotes.txt")
        service_instance.migrate_file.assert_any_call(
            "root/sub/2025-01-02-DailyNotes.txt"
        )
        assert service_instance.migrate_file.call_count == 2
        service_instance.migration_info.assert_called_once()

    def test_migrate_daily_logs_error_for_missing_path(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        service_instance = mocker.MagicMock()
        mocker.patch(
            "taskjournal.cli.commands.migrate.MigrationService",
            return_value=service_instance,
        )
        mocker.patch(
            "taskjournal.cli.commands.migrate.os.path.isfile", return_value=False
        )
        mocker.patch(
            "taskjournal.cli.commands.migrate.os.path.isdir", return_value=False
        )
        logger = mocker.patch("taskjournal.cli.commands.migrate.logger")

        # when
        result = invoke_cli(["migrate", "daily", "missing/path"])

        # then
        assert result.exit_code == 0
        logger.error.assert_called_once_with("Path not found: missing/path")
        service_instance.migrate_file.assert_not_called()
        service_instance.migration_info.assert_called_once()
