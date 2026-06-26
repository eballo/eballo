from collections.abc import Callable
from unittest.mock import MagicMock

from datetime import datetime

from freezegun import freeze_time
from typer.testing import Result


class TestDailyTime:

    @freeze_time("2025-01-19 10:00:00")
    def test_daily_time_happy_path(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["daily", "time"])

        # then
        assert result.exit_code == 0
        manager_instance.daily_time.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0)
        )
