from collections.abc import Callable
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from freezegun import freeze_time
from typer.testing import Result


class TestReportQuarter:

    @freeze_time("2026-07-01 10:00:00")
    def test_quarter_creates_report(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.create_quarter_review = AsyncMock(return_value=None)
        result = invoke_cli(["report", "quarter"])
        assert result.exit_code == 0
        cli_manager.create_quarter_review.assert_called_once_with(datetime(2026, 7, 1, 10, 0))

    @freeze_time("2026-07-01 10:00:00")
    def test_quarter_with_custom_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.create_quarter_review = AsyncMock(return_value=None)
        result = invoke_cli(["report", "quarter", "--date", "2026-01-15"])
        assert result.exit_code == 0
        cli_manager.create_quarter_review.assert_called_once_with(datetime(2026, 1, 15))


class TestReportYear:

    @freeze_time("2026-07-01 10:00:00")
    def test_year_creates_report(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.create_year_review = AsyncMock(return_value=None)
        result = invoke_cli(["report", "year"])
        assert result.exit_code == 0
        cli_manager.create_year_review.assert_called_once_with(datetime(2026, 7, 1, 10, 0))

    @freeze_time("2026-07-01 10:00:00")
    def test_year_with_custom_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.create_year_review = AsyncMock(return_value=None)
        result = invoke_cli(["report", "year", "--date", "2025-12-01"])
        assert result.exit_code == 0
        cli_manager.create_year_review.assert_called_once_with(datetime(2025, 12, 1))


class TestReportCompare:

    @freeze_time("2026-07-01 10:00:00")
    def test_compare_months_shows_table(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.compare_periods.return_value = [
            {"label": "Jan 2026", "total_worked_days": 20, "vacation_days": 1, "days_at_office": 10, "days_at_home": 10, "total_time_seconds": 288000},
            {"label": "Feb 2026", "total_worked_days": 18, "vacation_days": 2, "days_at_office": 8, "days_at_home": 10, "total_time_seconds": 259200},
        ]
        result = invoke_cli(["report", "compare", "months"])
        assert result.exit_code == 0
        assert "Jan 2026" in result.output
        assert "Feb 2026" in result.output
        cli_manager.compare_periods.assert_called_once_with("month", 2026)

    @freeze_time("2026-07-01 10:00:00")
    def test_compare_months_with_year(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.compare_periods.return_value = []
        invoke_cli(["report", "compare", "months", "--year", "2025"])
        cli_manager.compare_periods.assert_called_once_with("month", 2025)

    @freeze_time("2026-07-01 10:00:00")
    def test_compare_quarters_shows_table(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.compare_periods.return_value = [
            {"label": "Q1 2026", "total_worked_days": 55, "vacation_days": 5, "days_at_office": 25, "days_at_home": 30, "total_time_seconds": 864000},
            {"label": "Q2 2026", "total_worked_days": 60, "vacation_days": 3, "days_at_office": 30, "days_at_home": 30, "total_time_seconds": 936000},
        ]
        result = invoke_cli(["report", "compare", "quarters"])
        assert result.exit_code == 0
        assert "Q1 2026" in result.output
        cli_manager.compare_periods.assert_called_once_with("quarter", 2026)

    @freeze_time("2026-07-01 10:00:00")
    def test_compare_quarters_with_year(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.compare_periods.return_value = []
        invoke_cli(["report", "compare", "quarters", "--year", "2025"])
        cli_manager.compare_periods.assert_called_once_with("quarter", 2025)
