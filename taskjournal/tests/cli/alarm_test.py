from collections.abc import Callable
from datetime import datetime
from unittest.mock import MagicMock

from freezegun import freeze_time
from pytest import LogCaptureFixture
from pytest_mock import MockerFixture
from typer.testing import Result


class TestAlarmList:

    def test_alarm_list_shows_no_alarms_message(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_alarms.return_value = []

        result = invoke_cli(["alarm", "list"])

        assert result.exit_code == 0
        assert "No alarm files found" in result.output

    def test_alarm_list_shows_active_alarm(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_alarms.return_value = [
            {
                "date": "2025-01-15",
                "job_id": "wk:2025-01-15:17:30",
                "scheduled": "17:30",
                "message": "Time to wrap up!",
                "is_past": False,
                "is_alive": True,
            }
        ]

        result = invoke_cli(["alarm", "list"])

        assert result.exit_code == 0
        assert "2025-01-15" in result.output
        assert "active" in result.output

    def test_alarm_list_shows_expired_alarm(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_alarms.return_value = [
            {
                "date": "2025-01-14",
                "job_id": "wk:2025-01-14:17:00",
                "scheduled": "17:00",
                "message": None,
                "is_past": True,
                "is_alive": False,
            }
        ]

        result = invoke_cli(["alarm", "list"])

        assert result.exit_code == 0
        assert "expired" in result.output

    def test_alarm_list_shows_stopped_alarm(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_alarms.return_value = [
            {
                "date": "2025-01-13",
                "job_id": "wk:2025-01-13:17:00",
                "scheduled": None,
                "message": "Custom message",
                "is_past": False,
                "is_alive": False,
            }
        ]

        result = invoke_cli(["alarm", "list"])

        assert result.exit_code == 0
        assert "stopped" in result.output


class TestAlarmCancel:

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_cancel_for_today(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.cancel_alarm_for_date.return_value = True

        result = invoke_cli(["alarm", "cancel"])

        assert result.exit_code == 0
        cli_manager.cancel_alarm_for_date.assert_called_once()

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_cancel_for_specific_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.cancel_alarm_for_date.return_value = True

        result = invoke_cli(["alarm", "cancel", "--date", "2025-01-14"])

        assert result.exit_code == 0
        called_date = cli_manager.cancel_alarm_for_date.call_args[0][0]
        assert called_date.strftime("%Y-%m-%d") == "2025-01-14"

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_cancel_no_alarm_found_warns(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.cancel_alarm_for_date.return_value = False

        result = invoke_cli(["alarm", "cancel"])

        assert result.exit_code == 0
        assert "No alarm file found" in caplog.text

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_cancel_all_with_no_alarms(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_alarms.return_value = []

        result = invoke_cli(["alarm", "cancel", "--all"])

        assert result.exit_code == 0
        assert "No alarms to cancel" in result.output

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_cancel_all_cancels_each(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_alarms.return_value = [
            {"date": "2025-01-14", "job_id": "abc"},
            {"date": "invalid-date", "job_id": "xyz"},
        ]
        cli_manager.cancel_alarm_for_date.return_value = True

        result = invoke_cli(["alarm", "cancel", "--all"])

        assert result.exit_code == 0
        cli_manager.cancel_alarm_for_date.assert_called_once()


class TestAlarmSet:

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_set_for_today(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(["alarm", "set", "--time", "17:30"])

        assert result.exit_code == 0
        cli_manager.set_alarm.assert_called_once()
        _, alarm_time, message = cli_manager.set_alarm.call_args[0]
        assert alarm_time.hour == 17
        assert alarm_time.minute == 30
        assert message == "Time to wrap up!"

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_set_with_custom_message(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(["alarm", "set", "--time", "18:00", "--message", "Go home!"])

        assert result.exit_code == 0
        _, alarm_time, message = cli_manager.set_alarm.call_args[0]
        assert message == "Go home!"

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_set_for_specific_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(["alarm", "set", "--time", "17:00", "--date", "2025-01-16"])

        assert result.exit_code == 0
        target_date, alarm_time, _ = cli_manager.set_alarm.call_args[0]
        assert target_date.strftime("%Y-%m-%d") == "2025-01-16"

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_set_invalid_time_logs_error(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        result = invoke_cli(["alarm", "set", "--time", "not-a-time"])

        assert result.exit_code == 0
        assert "Invalid time format" in caplog.text
        cli_manager.set_alarm.assert_not_called()
