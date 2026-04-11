from collections.abc import Callable
from datetime import datetime
from unittest.mock import MagicMock

from freezegun import freeze_time
from pytest import LogCaptureFixture
from typer.testing import Result


class TestInfoCommand:

    @freeze_time("2025-01-15 10:00:00")
    def test_show_info_happy_path(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["info", "show"])

        # then
        assert result.exit_code == 0
        manager_instance.show_info.assert_called_once_with(
            datetime(2025, 1, 15, 10, 0, 0)
        )

    @freeze_time("2025-01-15 10:00:00")
    def test_show_info_with_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["info", "show", "--date", "2025-08-31"])

        # then
        assert result.exit_code == 0
        manager_instance.show_info.assert_called_once_with(
            datetime(2025, 8, 31, 0, 0, 0)
        )

    def test_show_info_with_invalid_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["info", "show", "--date", "not-a-date"])

        # then
        assert "❌ Invalid date format. Use 'YYYY-MM-DD'." in caplog.text
        manager_instance.show_info.assert_not_called()
