from pytest_mock import MockerFixture
from collections.abc import Callable
from unittest.mock import MagicMock

from freezegun import freeze_time
from typer.testing import Result


class TestStatistics:

    @freeze_time("2026-03-01 10:00:00")
    def test_statistics_all_uses_default_year(
        self,
        cli_working_days: MagicMock,
        cli_container: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # when
        result = invoke_cli(["statistics", "all"])

        # then
        assert result.exit_code == 0
        cli_container.working_days_service.assert_called_once_with(year=2026, debug=False)
        cli_working_days.summary.assert_called_once()

    def test_statistics_progress_uses_explicit_year(
        self,
        cli_working_days: MagicMock,
        cli_container: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # when
        result = invoke_cli(["statistics", "progress", "--year", "2031"])

        # then
        assert result.exit_code == 0
        cli_container.working_days_service.assert_called_once_with(year="2031", debug=False)
        cli_working_days.get_progress.assert_called_once()

    def test_statistics_real_uses_debug_flag(
        self,
        cli_working_days: MagicMock,
        cli_container: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # when
        result = invoke_cli(["--debug", "statistics", "real", "--year", "2027"])

        # then
        assert result.exit_code == 0
        cli_container.working_days_service.assert_called_once_with(year="2027", debug=True)
        cli_working_days.get_real_working_days.assert_called_once()
