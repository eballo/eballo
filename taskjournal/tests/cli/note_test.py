from collections.abc import Callable
from unittest.mock import MagicMock

from pytest_mock import MockerFixture
from typer.testing import Result


class TestNote:

    def test_note_add_calls_manager(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.add_note_to_daily = mocker.MagicMock()

        result = invoke_cli(["note", "Fixed the login timeout bug"])

        assert result.exit_code == 0
        cli_manager.add_note_to_daily.assert_called_once()
        _, text = cli_manager.add_note_to_daily.call_args[0]
        assert text == "Fixed the login timeout bug"

    def test_note_add_logs_error_on_file_not_found(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.add_note_to_daily = mocker.MagicMock(
            side_effect=FileNotFoundError("No daily notes for 2026-07-02")
        )
        err = mocker.patch("taskjournal.cli.commands.note.logger.error")

        result = invoke_cli(["note", "some text"])

        assert result.exit_code == 1
        err.assert_called_once()

    def test_note_add_logs_error_on_missing_section(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.add_note_to_daily = mocker.MagicMock(
            side_effect=ValueError("Notes section not found")
        )
        err = mocker.patch("taskjournal.cli.commands.note.logger.error")

        result = invoke_cli(["note", "some text"])

        assert result.exit_code == 1
        err.assert_called_once()
