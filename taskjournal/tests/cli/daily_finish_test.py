from collections.abc import Callable
from unittest.mock import MagicMock

from datetime import datetime

from _pytest.logging import LogCaptureFixture
from freezegun import freeze_time
from typer.testing import Result


class TestDailyFinish:

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_finish_happy_path(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["daily", "finish"])

        # then
        assert result.exit_code == 0
        manager_instance.finalize_daily_notes.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0)
        )

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_finish_debug(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["--debug", "daily", "finish"])

        # then
        assert result.exit_code == 0
        manager_instance.finalize_daily_notes.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0)
        )
        assert "date=None, debug=True" in caplog.text

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_finish_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["daily", "finish", "--date", "2025-01-20 10:00"])

        # then
        assert result.exit_code == 0
        manager_instance.finalize_daily_notes.assert_called_once_with(
            datetime(2025, 1, 20, 10, 0, 0)
        )

    def test_daily_finish_date__no_valid_value(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["daily", "finish", "--date", "some-invalid-value"])

        # then
        assert result.exit_code == 1
        assert "❌ Invalid date format. Use 'YYYY-MM-DD HH:MM'." in caplog.text
        manager_instance.finalize_daily_notes.assert_not_called()
