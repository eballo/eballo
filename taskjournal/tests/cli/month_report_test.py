from pytest_mock import MockerFixture
from collections.abc import Callable
from unittest.mock import MagicMock

from datetime import datetime

from freezegun import freeze_time
from typer.testing import Result


class TestMonthReport:

    @freeze_time("2025-01-19 10:00:00")
    def test_month_report_happy_path(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager
        manager_instance.create_month_review = mocker.AsyncMock()

        # when
        result = invoke_cli(["month", "report"])

        # then
        assert result.exit_code == 0
        manager_instance.create_month_review.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0)
        )
