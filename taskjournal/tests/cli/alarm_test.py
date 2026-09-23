from collections.abc import Callable
from datetime import datetime
from unittest.mock import MagicMock, call

from freezegun import freeze_time
from pytest import LogCaptureFixture, mark
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
        cli_manager.list_alarms.assert_called_once_with()

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
        assert "17:30" in result.output
        assert "Time to wrap up!" in result.output
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
        assert "2025-01-14" in result.output
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
            }
        ]

        result = invoke_cli(["alarm", "list"])

        assert result.exit_code == 0
        assert "Custom message" in result.output
        assert "stopped" in result.output

    def test_alarm_list_alive_alarm_is_active_even_when_past(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_alarms.return_value = [
            {
                "date": "2025-01-13",
                "job_id": "wk:2025-01-13:17:00",
                "scheduled": "17:00",
                "is_past": True,
                "is_alive": True,
            }
        ]

        result = invoke_cli(["alarm", "list"])

        assert result.exit_code == 0
        assert "active" in result.output
        assert "expired" not in result.output


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
        cli_manager.list_alarms.assert_not_called()
        cli_manager.cancel_alarm_for_date.assert_called_once_with(
            datetime(2025, 1, 15, 10)
        )

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_cancel_for_specific_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.cancel_alarm_for_date.return_value = True

        result = invoke_cli(["alarm", "cancel", "--date", "2025-01-14"])

        assert result.exit_code == 0
        cli_manager.list_alarms.assert_not_called()
        cli_manager.cancel_alarm_for_date.assert_called_once_with(datetime(2025, 1, 14))

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
        cli_manager.cancel_alarm_for_date.assert_called_once_with(
            datetime(2025, 1, 15, 10)
        )

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
        cli_manager.list_alarms.assert_called_once_with()
        cli_manager.cancel_alarm_for_date.assert_not_called()

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_cancel_all_cancels_each(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_alarms.return_value = [
            {"date": "2025-01-14", "job_id": "abc"},
            {"date": "invalid-date", "job_id": "xyz"},
            {"date": "2025-02-30", "job_id": "bad"},
            {"date": "2025-01-16", "job_id": "def"},
        ]
        cli_manager.cancel_alarm_for_date.return_value = True

        result = invoke_cli(["alarm", "cancel", "--all"])

        assert result.exit_code == 0
        cli_manager.list_alarms.assert_called_once_with()
        assert cli_manager.cancel_alarm_for_date.call_args_list == [
            call(datetime(2025, 1, 14)),
            call(datetime(2025, 1, 16)),
        ]


class TestAlarmSet:

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_set_for_today(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(["alarm", "set", "--time", "17:30"])

        assert result.exit_code == 0
        cli_manager.set_alarm.assert_called_once_with(
            datetime(2025, 1, 15, 10),
            datetime(2025, 1, 15, 17, 30),
            "Time to wrap up!",
        )

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_set_with_custom_message(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(
            ["alarm", "set", "--time", "18:00", "--message", "Go home!"]
        )

        assert result.exit_code == 0
        cli_manager.set_alarm.assert_called_once_with(
            datetime(2025, 1, 15, 10), datetime(2025, 1, 15, 18), "Go home!"
        )

    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_set_for_specific_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli(["alarm", "set", "--time", "17:00", "--date", "2025-01-16"])

        assert result.exit_code == 0
        cli_manager.set_alarm.assert_called_once_with(
            datetime(2025, 1, 16), datetime(2025, 1, 16, 17), "Time to wrap up!"
        )

    @mark.parametrize("invalid_time", ["not-a-time", "25:00", "17:60"])
    @freeze_time("2025-01-15 10:00:00")
    def test_alarm_set_invalid_time_logs_error(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
        invalid_time: str,
    ) -> None:
        result = invoke_cli(["alarm", "set", "--time", invalid_time])

        assert result.exit_code == 0
        assert f"Invalid time format '{invalid_time}'" in caplog.text
        cli_manager.set_alarm.assert_not_called()
