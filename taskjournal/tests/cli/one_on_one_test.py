from collections.abc import Callable
from unittest.mock import MagicMock

from datetime import datetime

from freezegun import freeze_time
from pytest import LogCaptureFixture
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
        result = invoke_cli(["report", "1on1", "create"])

        # then
        assert result.exit_code == 0
        manager_instance.create_one_on_one.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0), person_name=""
        )

    @freeze_time("2025-01-19 10:00:00")
    def test_add_topic_calls_manager(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        result = invoke_cli(["report", "1on1", "add-topic", "-t", "My topic"])

        assert result.exit_code == 0
        cli_manager.add_topic_to_one_on_one.assert_called_once_with(
            datetime(2025, 1, 19, 10, 0, 0), "My topic"
        )
        assert "Added topic: My topic" in caplog.text

    @freeze_time("2025-01-19 10:00:00")
    def test_add_topic_logs_error_on_file_not_found(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.add_topic_to_one_on_one.side_effect = FileNotFoundError("no file")

        result = invoke_cli(["report", "1on1", "add-topic", "-t", "topic"])

        assert result.exit_code == 0
        assert "no file" in caplog.text

    @freeze_time("2025-01-19 10:00:00")
    def test_add_topic_logs_error_on_value_error(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.add_topic_to_one_on_one.side_effect = ValueError("no section")

        result = invoke_cli(["report", "1on1", "add-topic", "-t", "topic"])

        assert result.exit_code == 0
        assert "no section" in caplog.text
