from collections.abc import Callable
from unittest.mock import MagicMock

from datetime import datetime

from _pytest.logging import LogCaptureFixture
from freezegun import freeze_time
from pytest_mock import MockerFixture
from typer.testing import Result


class TestDailyFinish:

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_finish_happy_path(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.finalize_daily_notes = mocker.AsyncMock()
        result = invoke_cli(["daily", "finish"])
        assert result.exit_code == 0
        cli_manager.finalize_daily_notes.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0), no_summary=False, force=False
        )

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_finish_no_summary(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.finalize_daily_notes = mocker.AsyncMock()
        result = invoke_cli(["daily", "finish", "--no-summary"])
        assert result.exit_code == 0
        cli_manager.finalize_daily_notes.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0), no_summary=True, force=False
        )

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_finish_force(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.finalize_daily_notes = mocker.AsyncMock()
        result = invoke_cli(["daily", "finish", "--force"])
        assert result.exit_code == 0
        cli_manager.finalize_daily_notes.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0), no_summary=False, force=True
        )

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_finish_debug(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.finalize_daily_notes = mocker.AsyncMock()
        result = invoke_cli(["--debug", "daily", "finish"])
        assert result.exit_code == 0
        cli_manager.finalize_daily_notes.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0), no_summary=False, force=False
        )
        assert "date=None, debug=True" in caplog.text

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_finish_date(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.finalize_daily_notes = mocker.AsyncMock()
        result = invoke_cli(["daily", "finish", "--date", "2025-01-20 10:00"])
        assert result.exit_code == 0
        cli_manager.finalize_daily_notes.assert_called_once_with(
            datetime(2025, 1, 20, 10, 0, 0), no_summary=False, force=False
        )

    def test_daily_finish_date__no_valid_value(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.finalize_daily_notes = mocker.AsyncMock()
        result = invoke_cli(["daily", "finish", "--date", "some-invalid-value"])
        assert result.exit_code == 1
        assert "❌ Invalid date format. Use 'YYYY-MM-DD HH:MM'." in caplog.text
        cli_manager.finalize_daily_notes.assert_not_called()
