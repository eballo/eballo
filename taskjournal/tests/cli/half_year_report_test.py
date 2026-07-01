from collections.abc import Callable
from datetime import datetime
from unittest.mock import MagicMock

from freezegun import freeze_time
from pytest_mock import MockerFixture
from typer.testing import Result


class TestHalfYearReport:

    @freeze_time("2025-01-19 10:00:00")
    def test_half_year_report_happy_path(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        manager_instance = cli_manager
        manager_instance.create_half_year_review = mocker.AsyncMock()

        result = invoke_cli(["report", "half-year"])

        assert result.exit_code == 0
        manager_instance.create_half_year_review.assert_awaited_once_with(
            datetime(2025, 1, 19, 10, 0, 0)
        )
