from collections.abc import Callable
from datetime import date
from unittest.mock import MagicMock

from freezegun import freeze_time
from typer.testing import Result


class TestStatistics:

    @freeze_time("2026-03-01 10:00:00")
    def test_completion_shows_table(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_completion_stats.return_value = [
            ("2026-02-01", 5, 6),
            ("2026-02-02", 3, 3),
        ]
        result = invoke_cli(["statistics", "completion"])
        assert result.exit_code == 0
        cli_manager.get_completion_stats.assert_called_once_with(2026)

    @freeze_time("2026-03-01 10:00:00")
    def test_completion_with_explicit_year(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_completion_stats.return_value = [("2025-06-01", 4, 5)]
        result = invoke_cli(["statistics", "completion", "--year", "2025"])
        assert result.exit_code == 0
        cli_manager.get_completion_stats.assert_called_once_with(2025)

    @freeze_time("2026-03-01 10:00:00")
    def test_completion_warns_when_no_data(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_completion_stats.return_value = []
        result = invoke_cli(["statistics", "completion"])
        assert result.exit_code == 0
        assert "No daily notes" in result.output

    @freeze_time("2026-03-01 10:00:00")
    def test_workload_shows_table(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_workload_stats.return_value = [
            ("W01", 36000),
            ("W02", 180000),
        ]
        result = invoke_cli(["statistics", "workload"])
        assert result.exit_code == 0
        cli_manager.get_workload_stats.assert_called_once_with(2026)

    @freeze_time("2026-03-01 10:00:00")
    def test_workload_warns_when_no_data(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_workload_stats.return_value = []
        result = invoke_cli(["statistics", "workload"])
        assert result.exit_code == 0
        assert "No workload" in result.output

    @freeze_time("2026-03-01 10:00:00")
    def test_patterns_shows_stats(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_pattern_stats.return_value = {
            "best_day": "Monday",
            "best_hour": 9,
            "avg_done_per_day": 4.2,
            "carry_over_rate": 15,
            "avg_by_day": {"Monday": 5.0, "Tuesday": 3.5},
        }
        result = invoke_cli(["statistics", "patterns"])
        assert result.exit_code == 0
        assert "Monday" in result.output
        cli_manager.get_pattern_stats.assert_called_once_with(2026)

    @freeze_time("2026-03-01 10:00:00")
    def test_patterns_without_best_day_or_hour(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_pattern_stats.return_value = {
            "best_day": None,
            "best_hour": None,
            "avg_done_per_day": 0,
            "carry_over_rate": 0,
            "avg_by_day": {},
        }
        result = invoke_cli(["statistics", "patterns"])
        assert result.exit_code == 0

    @freeze_time("2026-03-01 10:00:00")
    def test_tags_shows_epic_data(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_tags_stats.return_value = [
            ("Platform", 20),
            ("Infra", 10),
        ]
        result = invoke_cli(["statistics", "tags"])
        assert result.exit_code == 0
        assert "Platform" in result.output
        cli_manager.get_tags_stats.assert_called_once_with(2026)

    @freeze_time("2026-03-01 10:00:00")
    def test_tags_warns_when_no_data(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_tags_stats.return_value = []
        result = invoke_cli(["statistics", "tags"])
        assert result.exit_code == 0
        assert "No epic tags" in result.output

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
