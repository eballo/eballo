from collections.abc import Callable
from datetime import date
from unittest.mock import MagicMock

from freezegun import freeze_time
from typer.testing import Result


class TestStatistics:

    @freeze_time("2026-03-01 10:00:00")
    def test_statistics_all_uses_default_year(
        self,
        cli_working_days: tuple[MagicMock, MagicMock],
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        factory, service = cli_working_days

        # when
        result = invoke_cli(["statistics", "all"])

        # then
        assert result.exit_code == 0
        factory.assert_called_once_with(year="2026", debug=False)
        service.summary.assert_called_once()

    def test_statistics_progress_uses_explicit_year(
        self,
        cli_working_days: tuple[MagicMock, MagicMock],
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        factory, service = cli_working_days

        # when
        result = invoke_cli(["statistics", "progress", "--year", "2031"])

        # then
        assert result.exit_code == 0
        factory.assert_called_once_with(year="2031", debug=False)
        service.get_progress.assert_called_once()

    def test_statistics_real_uses_debug_flag(
        self,
        cli_working_days: tuple[MagicMock, MagicMock],
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        factory, service = cli_working_days

        # when
        result = invoke_cli(["--debug", "statistics", "real", "--year", "2027"])

        # then
        assert result.exit_code == 0
        factory.assert_called_once_with(year="2027", debug=True)
        service.get_real_working_days.assert_called_once()

    @freeze_time("2026-03-01 10:00:00")
    def test_streak_calls_manager_and_shows_output(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_streak_stats.return_value = {
            "current": 7,
            "longest": 14,
            "longest_start": date(2026, 1, 1),
            "longest_end": date(2026, 1, 20),
            "total": 50,
        }

        result = invoke_cli(["statistics", "streak"])

        assert result.exit_code == 0
        assert "7 days" in result.output
        assert "14 days" in result.output
        assert "50" in result.output

    @freeze_time("2026-03-01 10:00:00")
    def test_streak_singular_day(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_streak_stats.return_value = {
            "current": 1,
            "longest": 1,
            "longest_start": date(2026, 3, 1),
            "longest_end": date(2026, 3, 1),
            "total": 1,
        }

        result = invoke_cli(["statistics", "streak"])

        assert result.exit_code == 0
        assert "1 day" in result.output
        assert "1 days" not in result.output

    @freeze_time("2026-03-01 10:00:00")
    def test_streak_zero_current_shows_dim(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_streak_stats.return_value = {
            "current": 0,
            "longest": 5,
            "longest_start": date(2025, 6, 1),
            "longest_end": date(2025, 6, 7),
            "total": 10,
        }

        result = invoke_cli(["statistics", "streak"])

        assert result.exit_code == 0
        assert "0 days" in result.output
