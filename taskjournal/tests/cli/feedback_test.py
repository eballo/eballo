from collections.abc import Callable
from datetime import datetime
from unittest.mock import MagicMock

from freezegun import freeze_time
from typer.testing import Result


class TestFeedbackCLI:

    @freeze_time("2026-07-01 10:00:00")
    def test_received_records_feedback(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli([
            "feedback", "received", "Great PR review",
            "--from", "Maria", "--context", "PR #142",
        ])
        assert result.exit_code == 0
        cli_manager.add_feedback_received.assert_called_once_with(
            "Great PR review", "Maria", "PR #142", datetime(2026, 7, 1, 10, 0)
        )
        assert "Maria" in result.output

    @freeze_time("2026-07-01 10:00:00")
    def test_received_with_custom_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli([
            "feedback", "received", "Good job",
            "--from", "Bob", "--date", "2026-06-15",
        ])
        assert result.exit_code == 0
        cli_manager.add_feedback_received.assert_called_once_with(
            "Good job", "Bob", "", datetime(2026, 6, 15)
        )

    @freeze_time("2026-07-01 10:00:00")
    def test_given_records_feedback(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        result = invoke_cli([
            "feedback", "given", "Great ownership",
            "--to", "Alex", "--context", "1:1",
        ])
        assert result.exit_code == 0
        cli_manager.add_feedback_given.assert_called_once_with(
            "Great ownership", "Alex", "1:1", datetime(2026, 7, 1, 10, 0)
        )
        assert "Alex" in result.output

    @freeze_time("2026-07-01 10:00:00")
    def test_list_shows_entries(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_feedback.return_value = [
            {
                "type": "received",
                "date": "2026-07-01",
                "from_person": "Maria",
                "context": "PR #42",
                "text": "Excellent review",
            }
        ]
        result = invoke_cli(["feedback", "list"])
        assert result.exit_code == 0
        assert "Maria" in result.output
        assert "Excellent" in result.output

    @freeze_time("2026-07-01 10:00:00")
    def test_list_given_entries(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_feedback.return_value = [
            {
                "type": "given",
                "date": "2026-07-01",
                "to_person": "Alex",
                "context": "1:1",
                "text": "Good leadership",
            }
        ]
        result = invoke_cli(["feedback", "list"])
        assert result.exit_code == 0
        assert "Alex" in result.output

    @freeze_time("2026-07-01 10:00:00")
    def test_list_empty_shows_message(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_feedback.return_value = []
        result = invoke_cli(["feedback", "list"])
        assert result.exit_code == 0
        assert "No feedback" in result.output

    @freeze_time("2026-07-01 10:00:00")
    def test_list_filters_by_quarter(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_feedback.return_value = []
        invoke_cli(["feedback", "list", "--quarter", "2"])
        cli_manager.list_feedback.assert_called_once_with(
            year=2026, quarter=2, person=None, feedback_type=None
        )

    @freeze_time("2026-07-01 10:00:00")
    def test_list_filters_by_type(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_feedback.return_value = []
        invoke_cli(["feedback", "list", "--type", "received"])
        cli_manager.list_feedback.assert_called_once_with(
            year=2026, quarter=None, person=None, feedback_type="received"
        )
