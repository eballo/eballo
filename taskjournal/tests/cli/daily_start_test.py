from pytest_mock import MockerFixture
from unittest.mock import MagicMock

from datetime import datetime

from collections.abc import Callable
from freezegun import freeze_time
from pytest import LogCaptureFixture
from typer.testing import Result


class TestDailyStart:

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_start(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_manager.create_daily_notes = mocker.AsyncMock()

        # when
        result = invoke_cli(["daily", "start"])

        # then
        assert result.exit_code == 0
        cli_manager.create_daily_notes.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0), False, False, None, False, energy=None
        )

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_start_debug(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        cli_manager.create_daily_notes = mocker.AsyncMock()

        # when
        result = invoke_cli(["--debug", "daily", "start"])

        # then
        assert result.exit_code == 0
        cli_manager.create_daily_notes.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0), False, False, None, False, energy=None
        )
        assert "date=None, force=False, offline=False, debug=True" in caplog.text

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_start_force(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        cli_manager.create_daily_notes = mocker.AsyncMock()

        # when
        result = invoke_cli(["daily", "start", "--force"])

        # then
        assert result.exit_code == 0
        cli_manager.create_daily_notes.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0), True, False, None, False, energy=None
        )
        assert (
            "Force option is enabled. Existing daily notes file will be overwritten."
            in caplog.text
        )

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_start_date(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_manager.create_daily_notes = mocker.AsyncMock()

        # when
        result = invoke_cli(["daily", "start", "--date", "2025-01-20 10:00"])

        # then
        assert result.exit_code == 0
        cli_manager.create_daily_notes.assert_called_once_with(
            datetime(2025, 1, 20, 10, 0, 0), False, False, None, False, energy=None
        )

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_start_date_and_force(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        cli_manager.create_daily_notes = mocker.AsyncMock()

        # when
        result = invoke_cli(["daily", "start", "--date", "2025-01-20 10:00", "--force"])

        # then
        assert result.exit_code == 0
        cli_manager.create_daily_notes.assert_called_once_with(
            datetime(2025, 1, 20, 10, 0, 0), True, False, None, False, energy=None
        )
        assert (
            "Force option is enabled. Existing daily notes file will be overwritten."
            in caplog.text
        )

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_start_firefighter(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_manager.create_daily_notes = mocker.AsyncMock()

        # when
        result = invoke_cli(["daily", "start", "--ff"])

        # then
        assert result.exit_code == 0
        cli_manager.create_daily_notes.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0), False, True, None, False, energy=None
        )

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_start_work_from(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_manager.create_daily_notes = mocker.AsyncMock()

        # when
        result = invoke_cli(["daily", "start", "--w", "home"])

        # then
        assert result.exit_code == 0
        cli_manager.create_daily_notes.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0), False, False, "home", False, energy=None
        )

    def test_daily_start_date__no_valid_value(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        # when
        result = invoke_cli(["daily", "start", "--date", "some-invalid-value"])

        # then
        assert result.exit_code == 1
        assert "❌ Invalid date format. Use 'YYYY-MM-DD HH:MM'." in caplog.text
        cli_manager.create_daily_notes.assert_not_called()
