from pytest_mock import MockerFixture
from collections.abc import Callable

from freezegun import freeze_time
from typer.testing import Result


class TestStatistics:

    @freeze_time("2026-03-01 10:00:00")
    def test_statistics_all_uses_default_year(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        service_instance = mocker.MagicMock()
        service_cls = mocker.patch(
            "taskjournal.cli.commands.statistics.WorkingDaysService",
            return_value=service_instance,
        )

        # when
        result = invoke_cli(["statistics", "all"])

        # then
        assert result.exit_code == 0
        service_cls.assert_called_once_with(year=2026, debug=False)
        service_instance.summary.assert_called_once()

    def test_statistics_progress_uses_explicit_year(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        service_instance = mocker.MagicMock()
        service_cls = mocker.patch(
            "taskjournal.cli.commands.statistics.WorkingDaysService",
            return_value=service_instance,
        )

        # when
        result = invoke_cli(["statistics", "progress", "--year", "2031"])

        # then
        assert result.exit_code == 0
        service_cls.assert_called_once_with(year="2031", debug=False)
        service_instance.get_progress.assert_called_once()

    def test_statistics_real_uses_debug_flag(
        self,
        mocker: MockerFixture,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        service_instance = mocker.MagicMock()
        service_cls = mocker.patch(
            "taskjournal.cli.commands.statistics.WorkingDaysService",
            return_value=service_instance,
        )

        # when
        result = invoke_cli(["--debug", "statistics", "real", "--year", "2027"])

        # then
        assert result.exit_code == 0
        service_cls.assert_called_once_with(year="2027", debug=True)
        service_instance.get_real_working_days.assert_called_once()
