from collections.abc import Callable
from unittest.mock import MagicMock

from datetime import datetime

from freezegun import freeze_time
from pytest import LogCaptureFixture
from typer.testing import Result


class TestRetroCreate:

    @freeze_time("2025-01-19 10:00:00")
    def test_retro_create_happy_path(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["retro", "create"])

        # then
        assert result.exit_code == 0
        manager_instance.create_retro.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0)
        )

    def test_retro_create_invalid_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["retro", "create", "--date", "bad-date"])

        # then
        assert result.exit_code == 1
        assert "❌ Invalid date format. Use 'YYYY-MM-DD HH:MM'." in caplog.text
        manager_instance.create_retro.assert_not_called()
