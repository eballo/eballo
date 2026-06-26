from collections.abc import Callable
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
        # when
        result = invoke_cli(["info", "show"])

        # then
        assert result.exit_code == 0
        assert "Wednesday, 2025-01-15" in result.output

    @freeze_time("2025-01-15 10:00:00")
    def test_show_info_with_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # when
        result = invoke_cli(["info", "show", "--date", "2025-08-31"])

        # then
        assert result.exit_code == 0
        assert "2025-08-31" in result.output

    def test_show_info_with_invalid_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        # when
        result = invoke_cli(["info", "show", "--date", "not-a-date"])

        # then
        assert "❌ Invalid date format. Use 'YYYY-MM-DD'." in caplog.text
