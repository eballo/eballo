from collections.abc import Callable
from datetime import date, datetime

from freezegun import freeze_time
from pytest_mock import MockerFixture
from typer.testing import Result


class TestFireman:

    def _mock_service(self, mocker: MockerFixture) -> tuple:
        instance = mocker.MagicMock()
        cls = mocker.patch(
            "taskjournal.cli.commands.fireman.FiremanService",
            return_value=instance,
        )
        return cls, instance

    @freeze_time("2026-01-19 10:00:00")
    def test_fireman_add_calls_add_week(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        _, instance = self._mock_service(mocker)

        result = invoke_cli(["fireman", "add", "2026-01-19"])

        assert result.exit_code == 0
        instance.add_week.assert_called_once_with("2026-01-19")

    @freeze_time("2026-01-19 10:00:00")
    def test_fireman_list_prints_table(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        _, instance = self._mock_service(mocker)
        instance.get_all_weeks.return_value = [date(2026, 1, 12), date(2026, 1, 19), date(2026, 1, 26)]
        instance._get_monday.side_effect = lambda d: d - __import__("datetime").timedelta(days=d.weekday())

        result = invoke_cli(["fireman", "list"])

        assert result.exit_code == 0
        instance.get_all_weeks.assert_called_once()

    @freeze_time("2026-01-19 10:00:00")
    def test_fireman_list_empty(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        _, instance = self._mock_service(mocker)
        instance.get_all_weeks.return_value = []

        result = invoke_cli(["fireman", "list"])

        assert result.exit_code == 0

    @freeze_time("2026-01-19 10:00:00")
    def test_fireman_upcoming_calls_get_upcoming_weeks(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        _, instance = self._mock_service(mocker)
        instance.get_upcoming_weeks.return_value = [date(2026, 1, 19), date(2026, 1, 26)]
        instance._get_monday.return_value = date(2026, 1, 19)

        result = invoke_cli(["fireman", "upcoming"])

        assert result.exit_code == 0
        instance.get_upcoming_weeks.assert_called_once()

    @freeze_time("2026-01-19 10:00:00")
    def test_fireman_upcoming_empty(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        _, instance = self._mock_service(mocker)
        instance.get_upcoming_weeks.return_value = []

        result = invoke_cli(["fireman", "upcoming"])

        assert result.exit_code == 0

    @freeze_time("2026-01-19 10:00:00")
    def test_fireman_summary_calls_summary(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        _, instance = self._mock_service(mocker)

        result = invoke_cli(["fireman", "summary"])

        assert result.exit_code == 0
        instance.summary.assert_called_once_with(datetime(2026, 1, 19, 10, 0, 0).date())

    @freeze_time("2026-01-19 10:00:00")
    def test_fireman_list_with_explicit_year(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cls, instance = self._mock_service(mocker)
        instance.get_all_weeks.return_value = []

        result = invoke_cli(["fireman", "list", "--year", "2025"])

        assert result.exit_code == 0
        assert cls.call_args.kwargs["create_datetime"] == datetime(2025, 1, 1)
