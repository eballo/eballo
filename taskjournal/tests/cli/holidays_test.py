from collections.abc import Callable

from freezegun import freeze_time
from pytest_mock import MockerFixture
from typer.testing import Result

from taskjournal.config import TEMPLATE_FORMAT


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
        assert f"2026/holidays/holidays.{TEMPLATE_FORMAT}" in service_cls.call_args.kwargs["filepath"]
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
        assert f"2030/holidays/holidays.{TEMPLATE_FORMAT}" in service_cls.call_args.kwargs["filepath"]
        service_instance.summary_upcoming.assert_called_once()

    @freeze_time("2026-02-20 10:00:00")
    def test_holidays_past_calls_summary_past(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        service_instance = mocker.MagicMock()
        mocker.patch(
            "taskjournal.cli.commands.holidays.HolidayService",
            return_value=service_instance,
        )

        # when
        result = invoke_cli(["holidays", "past"])

        # then
        assert result.exit_code == 0
        service_instance.summary_past.assert_called_once()

    @freeze_time("2026-02-20 10:00:00")
    def test_holidays_summary_calls_summary(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        service_instance = mocker.MagicMock()
        mocker.patch(
            "taskjournal.cli.commands.holidays.HolidayService",
            return_value=service_instance,
        )

        # when
        result = invoke_cli(["holidays", "summary"])

        # then
        assert result.exit_code == 0
        service_instance.summary.assert_called_once()

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

    @freeze_time("2026-02-20 10:00:00")
    def test_holidays_add_calls_add_holiday(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        service_instance = mocker.MagicMock()
        mocker.patch(
            "taskjournal.cli.commands.holidays.HolidayService",
            return_value=service_instance,
        )

        result = invoke_cli(["holidays", "add", "2026-03-01", "My holiday"])

        assert result.exit_code == 0
        service_instance.add_holiday.assert_called_once()
        call_args = service_instance.add_holiday.call_args[0]
        assert "2026-03-01" in call_args
        assert "My holiday" in call_args

    @freeze_time("2026-02-20 10:00:00")
    def test_holidays_days_until_next_holiday_prints_result(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        service_instance = mocker.MagicMock()
        service_instance.get_days_until_next_holiday.return_value = (
            5,
            "2026-02-25",
            "Carnival",
        )
        mocker.patch(
            "taskjournal.cli.commands.holidays.HolidayService",
            return_value=service_instance,
        )

        result = invoke_cli(["holidays", "days_until_next_holiday"])

        assert result.exit_code == 0
        assert "5" in result.output
        assert "Carnival" in result.output
