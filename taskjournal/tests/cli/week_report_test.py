from collections.abc import Callable
from unittest.mock import MagicMock

from datetime import datetime
from unittest.mock import AsyncMock

from freezegun import freeze_time
from pytest import LogCaptureFixture
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
