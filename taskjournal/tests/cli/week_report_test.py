from collections.abc import Callable
from datetime import datetime
from os.path import join
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from freezegun import freeze_time
from pytest import LogCaptureFixture
from pytest_mock import MockerFixture
from typer.testing import Result


class TestWeekReport:

    @freeze_time("2025-01-19 10:00:00")
    def test_week_report_happy_path(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager
        # when
        manager_instance.create_week_summary = AsyncMock()

        result = invoke_cli(["week", "report"])

        # then
        assert result.exit_code == 0
        manager_instance.create_week_summary.assert_awaited_once_with(
            datetime(2025, 1, 19, 10, 0, 0)
        )

    @freeze_time("2025-01-19 10:00:00")
    def test_week_report_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager
        # when
        manager_instance.create_week_summary = AsyncMock()

        result = invoke_cli(["week", "report", "--date", "2025-01-20"])

        # then
        assert result.exit_code == 0
        manager_instance.create_week_summary.assert_awaited_once_with(
            datetime(2025, 1, 20, 0, 0, 0)
        )

    def test_week_report_date__invalid_value(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        manager_instance = cli_manager
        # when
        manager_instance.create_week_summary = AsyncMock()

        result = invoke_cli(["week", "report", "--date", "not-a-date"])

        # then
        assert result.exit_code == 1
        assert "❌ Invalid date format. Use 'YYYY-MM-DD'." in caplog.text
        manager_instance.create_week_summary.assert_not_called()

    @freeze_time("2026-04-11 10:00:00")
    def test_week_recreate_since(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager
        # when
        manager_instance.recreate_week_summaries = AsyncMock()

        result = invoke_cli(["week", "recreate-since", "--date", "2026-04-01"])

        # then
        assert result.exit_code == 0
        manager_instance.recreate_week_summaries.assert_awaited_once_with(
            datetime(2026, 4, 1, 0, 0, 0), datetime(2026, 4, 11, 10, 0, 0)
        )

    @freeze_time("2026-04-11 10:00:00")
    def test_week_recreate_since_invalid_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        manager_instance = cli_manager
        # when
        manager_instance.recreate_week_summaries = AsyncMock()

        result = invoke_cli(["week", "recreate-since", "--date", "invalid"])

        # then
        assert result.exit_code == 1
        assert "❌ Invalid date format. Use 'YYYY-MM-DD'." in caplog.text

    @freeze_time("2026-04-11 10:00:00")
    def test_week_recreate_since_future_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        manager_instance = cli_manager
        # when
        manager_instance.recreate_week_summaries = AsyncMock()

        result = invoke_cli(["week", "recreate-since", "--date", "2026-04-20"])

        # then
        assert result.exit_code == 1
        assert "❌ Start date cannot be in the future." in caplog.text

    @freeze_time("2026-01-21 10:00:00")
    def test_week_list_missing_files_show_missing_row(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
    ) -> None:
        # Monday 2026-01-19 is the week
        mocker.patch(
            "taskjournal.cli.commands.week.TimeService.get_week_folder_and_daily_notes_file",
            return_value=("/week/folder", "/week/folder/2026-01-21-DailyNotes.md"),
        )
        cli_manager.time_service.get_daily_notes_name.side_effect = (
            lambda d: f"{d.strftime('%Y-%m-%d')}-DailyNotes.md"
        )
        mocker.patch("taskjournal.cli.commands.week.exists", return_value=False)

        result = invoke_cli(["week", "list"])

        assert result.exit_code == 0
        assert "missing" in result.output

    @freeze_time("2026-01-21 10:00:00")
    def test_week_list_finalized_file_shows_status(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
        tmp_path: MockerFixture,
    ) -> None:
        week_folder = str(tmp_path)
        mocker.patch(
            "taskjournal.cli.commands.week.TimeService.get_week_folder_and_daily_notes_file",
            return_value=(week_folder, join(week_folder, "2026-01-19-DailyNotes.md")),
        )
        cli_manager.time_service.get_daily_notes_name.side_effect = (
            lambda d: f"{d.strftime('%Y-%m-%d')}-DailyNotes.md"
        )
        mocker.patch("taskjournal.cli.commands.week.exists", return_value=True)
        mocker.patch(
            "taskjournal.cli.commands.week.FileService.check_finalized_in_file",
            return_value=True,
        )
        mocker.patch(
            "taskjournal.cli.commands.week.TimeService.calculate_working_hours",
            return_value=(None, 8.0, None),
        )
        mocker.patch(
            "taskjournal.cli.commands.week.TimeService.seconds_to_hours_minutes",
            return_value=(8, 0),
        )

        result = invoke_cli(["week", "list"])

        assert result.exit_code == 0
        assert "finalized" in result.output

    @freeze_time("2026-01-21 10:00:00")
    def test_week_list_with_explicit_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "taskjournal.cli.commands.week.TimeService.get_week_folder_and_daily_notes_file",
            return_value=("/week/folder", "/week/folder/2026-01-05-DailyNotes.md"),
        )
        cli_manager.time_service.get_daily_notes_name.side_effect = (
            lambda d: f"{d.strftime('%Y-%m-%d')}-DailyNotes.md"
        )
        mocker.patch("taskjournal.cli.commands.week.exists", return_value=False)

        result = invoke_cli(["week", "list", "--date", "2026-01-05"])

        assert result.exit_code == 0
        assert "2026-01-05" in result.output
