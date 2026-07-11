from collections.abc import Callable
from unittest.mock import MagicMock

from freezegun import freeze_time
from pytest import LogCaptureFixture
from pytest_mock import MockerFixture
from typer.testing import Result

from taskjournal.container import AppContainer
from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Status, Task


class TestInfoCommand:

    def _patch_info_dependencies(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.cli.commands.info.exists", return_value=False)
        mocker.patch(
            "taskjournal.cli.commands.info.TimeService.resolve_daily_notes_file",
            return_value=("/fake/2025-01-15-DailyNotes.md", "/fake/week3"),
        )
        mocker.patch(
            "taskjournal.cli.commands.info.TimeService.get_accumulated_week_seconds",
            return_value=0,
        )
        mocker.patch(
            "taskjournal.cli.commands.info.HolidayService",
            side_effect=Exception("no holidays file"),
        )
        mocker.patch(
            "taskjournal.cli.commands.info.FiremanService",
            side_effect=Exception("no fireman file"),
        )

    @freeze_time("2025-01-15 10:00:00")
    def test_show_info_happy_path(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        self._patch_info_dependencies(mocker)

        result = invoke_cli(["info", "show"])

        assert result.exit_code == 0
        assert "Wednesday, 2025-01-15" in result.output

    @freeze_time("2025-01-15 10:00:00")
    def test_show_info_with_date(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        self._patch_info_dependencies(mocker)

        result = invoke_cli(["info", "show", "--date", "2025-08-31"])

        assert result.exit_code == 0
        assert "2025-08-31" in result.output

    def test_show_info_with_invalid_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        result = invoke_cli(["info", "show", "--date", "not-a-date"])

        assert "❌ Invalid date format. Use 'YYYY-MM-DD'." in caplog.text

    @freeze_time("2025-01-15 10:00:00")
    def test_show_info_with_existing_daily_notes_and_tasks(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        cli_container: AppContainer,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        mocker.patch("taskjournal.cli.commands.info.exists", return_value=True)
        mocker.patch(
            "taskjournal.cli.commands.info.TimeService.get_accumulated_week_seconds",
            return_value=28800,
        )
        mocker.patch(
            "taskjournal.cli.commands.info.HolidayService",
            side_effect=Exception("no holidays file"),
        )
        mocker.patch(
            "taskjournal.cli.commands.info.FiremanService",
            side_effect=Exception("no fireman file"),
        )
        tasks = [
            Task(id="1", description="Task A", status=Status.DONE),
            Task(id="2", description="Task B", status=Status.BLOCKED),
            Task(id="3", description="Task C", status=Status.IN_PROGRESS),
        ]
        note = ParsedNote(
            planned_tasks=tasks,
            end_time="17:30",
            work_from="Office",
        )
        cli_container.daily_parser().parse.return_value = note

        result = invoke_cli(["info", "show"])

        assert result.exit_code == 0
        assert "2025-01-15" in result.output

    @freeze_time("2025-01-15 10:00:00")
    def test_show_info_with_note_but_no_work_from_uses_wifi(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        cli_container: AppContainer,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        mocker.patch("taskjournal.cli.commands.info.exists", return_value=True)
        mocker.patch(
            "taskjournal.cli.commands.info.TimeService.get_accumulated_week_seconds",
            return_value=0,
        )
        mocker.patch(
            "taskjournal.cli.commands.info.HolidayService",
            side_effect=Exception("no holidays"),
        )
        mocker.patch(
            "taskjournal.cli.commands.info.FiremanService",
            side_effect=Exception("no fireman"),
        )
        note = ParsedNote(planned_tasks=[], work_from="", end_time="")
        cli_container.daily_parser().parse.return_value = note
        cli_manager.get_wifi_location.return_value = "Home"

        result = invoke_cli(["info", "show"])

        assert result.exit_code == 0
        cli_manager.get_wifi_location.assert_called()

    @freeze_time("2025-01-15 10:00:00")
    def test_show_info_with_holiday_service_configured(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        mocker.patch("taskjournal.cli.commands.info.exists", return_value=False)
        mocker.patch(
            "taskjournal.cli.commands.info.TimeService.resolve_daily_notes_file",
            return_value=("/fake/2025-01-15-DailyNotes.md", "/fake/week3"),
        )
        mocker.patch(
            "taskjournal.cli.commands.info.TimeService.get_accumulated_week_seconds",
            return_value=0,
        )

        mock_holiday_svc = MagicMock()
        mock_holiday_svc.is_holiday.return_value = None
        mock_holiday_svc.get_days_until_next_holiday.return_value = (5, None, "")
        mocker.patch("taskjournal.cli.commands.info.HolidayService", return_value=mock_holiday_svc)
        mocker.patch(
            "taskjournal.cli.commands.info.FiremanService",
            side_effect=Exception("no fireman"),
        )

        result = invoke_cli(["info", "show"])

        assert result.exit_code == 0

    @freeze_time("2025-01-15 10:00:00")
    def test_show_info_shows_holiday_name_when_today_is_holiday(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        mocker.patch("taskjournal.cli.commands.info.exists", return_value=False)
        mocker.patch(
            "taskjournal.cli.commands.info.TimeService.resolve_daily_notes_file",
            return_value=("/fake/2025-01-15-DailyNotes.md", "/fake/week3"),
        )
        mocker.patch(
            "taskjournal.cli.commands.info.TimeService.get_accumulated_week_seconds",
            return_value=0,
        )

        from datetime import date as _date
        mock_holiday_svc = MagicMock()
        mock_holiday_svc.is_holiday.return_value = {"description": "New Year's Day"}
        mock_holiday_svc.get_days_until_next_holiday.return_value = (10, _date(2025, 2, 1), "Some Holiday")
        mocker.patch("taskjournal.cli.commands.info.HolidayService", return_value=mock_holiday_svc)
        mocker.patch(
            "taskjournal.cli.commands.info.FiremanService",
            side_effect=Exception("no fireman"),
        )

        result = invoke_cli(["info", "show"])

        assert result.exit_code == 0
        assert "New Year" in result.output or "holiday" in result.output.lower()

    @freeze_time("2025-01-15 10:00:00")
    def test_show_info_with_fireman_service_configured(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        mocker.patch("taskjournal.cli.commands.info.exists", return_value=False)
        mocker.patch(
            "taskjournal.cli.commands.info.TimeService.resolve_daily_notes_file",
            return_value=("/fake/2025-01-15-DailyNotes.md", "/fake/week3"),
        )
        mocker.patch(
            "taskjournal.cli.commands.info.TimeService.get_accumulated_week_seconds",
            return_value=0,
        )
        mocker.patch(
            "taskjournal.cli.commands.info.HolidayService",
            side_effect=Exception("no holidays"),
        )

        from datetime import date as _date
        mock_fireman_svc = MagicMock()
        mock_fireman_svc.is_fireman_week.return_value = True
        mock_fireman_svc.get_next_week.return_value = (7, _date(2025, 1, 20))
        mocker.patch("taskjournal.cli.commands.info.FiremanService", return_value=mock_fireman_svc)

        result = invoke_cli(["info", "show"])

        assert result.exit_code == 0
        assert "firefighter" in result.output.lower()

    @freeze_time("2025-01-15 10:00:00")
    def test_show_info_package_not_found_uses_dev_version(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        self._patch_info_dependencies(mocker)
        from importlib.metadata import PackageNotFoundError
        mocker.patch(
            "taskjournal.cli.commands.info.version",
            side_effect=PackageNotFoundError("taskjournal"),
        )

        result = invoke_cli(["info", "show"])

        assert result.exit_code == 0
        assert "dev" in result.output
