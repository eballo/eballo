from collections.abc import Callable
from unittest.mock import MagicMock

from datetime import datetime

from freezegun import freeze_time
from typer.testing import Result


class TestOneOnOne:

    @freeze_time("2025-01-19 10:00:00")
    def test_one_on_one_report_calls_manager(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["1on1", "report"])

        # then
        assert result.exit_code == 0
        manager_instance.create_one_on_one.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0)
        )
