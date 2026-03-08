from pytest_mock import MockerFixture
from collections.abc import Callable

from freezegun import freeze_time
from typer.testing import Result


class TestHolidays:

    @freeze_time("2026-02-20 10:00:00")
    def test_holidays_all_uses_default_year_and_calls_summary_all(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        service_instance = mocker.MagicMock()
        service_cls = mocker.patch(
            "taskjournal.cli.commands.holidays.HolidayService",
            return_value=service_instance,
        )

        # when
        result = invoke_cli(["holidays", "all"])

        # then
        assert result.exit_code == 0
        service_cls.assert_called_once()
        assert "2026/holidays/holidays.md" in service_cls.call_args.kwargs["filepath"]
        service_instance.summary_all.assert_called_once()

    def test_holidays_upcoming_uses_explicit_year(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        service_instance = mocker.MagicMock()
        service_cls = mocker.patch(
            "taskjournal.cli.commands.holidays.HolidayService",
            return_value=service_instance,
        )

        # when
        result = invoke_cli(["holidays", "upcoming", "--year", "2030"])

        # then
        assert result.exit_code == 0
        service_cls.assert_called_once()
        assert "2030/holidays/holidays.md" in service_cls.call_args.kwargs["filepath"]
        service_instance.summary_upcoming.assert_called_once()

    @freeze_time("2026-02-20 10:00:00")
    def test_holidays_populate_uses_debug_flag(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        service_instance = mocker.MagicMock()
        service_cls = mocker.patch(
            "taskjournal.cli.commands.holidays.HolidayService",
            return_value=service_instance,
        )

        # when
        result = invoke_cli(["--debug", "holidays", "populate"])

        # then
        assert result.exit_code == 0
        assert service_cls.call_args.kwargs["debug"] is True
        service_instance.populate_files.assert_called_once()
