from collections.abc import Callable
from datetime import datetime
from unittest.mock import MagicMock

from freezegun import freeze_time
from typer.testing import Result


class TestStandup:

    @freeze_time("2025-01-20 09:00:00")
    def test_standup_shows_yesterday_done_today_planned_and_blockers(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_standup.return_value = {
            "done": ["Fix bug #123", "Review PR #456"],
            "today_done": [],
            "today": ["Write tests", "Deploy hotfix"],
            "blockers": ["Waiting on design"],
        }

        result = invoke_cli(["standup"])

        assert result.exit_code == 0
        assert "Fix bug #123" in result.output
        assert "Review PR #456" in result.output
        assert "Write tests" in result.output
        assert "Deploy hotfix" in result.output
        assert "Waiting on design" in result.output

    @freeze_time("2025-01-20 09:00:00")
    def test_standup_shows_done_today_section_when_tasks_completed(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_standup.return_value = {
            "done": ["Yesterday task"],
            "today_done": ["Morning hotfix", "Code review for PR #789"],
            "today": ["Afternoon feature"],
            "blockers": [],
        }

        result = invoke_cli(["standup"])

        assert result.exit_code == 0
        assert "Done today" in result.output
        assert "Morning hotfix" in result.output
        assert "Code review for PR #789" in result.output

    @freeze_time("2025-01-20 09:00:00")
    def test_standup_hides_done_today_section_when_empty(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_standup.return_value = {
            "done": ["Yesterday task"],
            "today_done": [],
            "today": ["Today task"],
            "blockers": [],
        }

        result = invoke_cli(["standup"])

        assert result.exit_code == 0
        assert "Done today" not in result.output

    @freeze_time("2025-01-20 09:00:00")
    def test_standup_shows_empty_sections_when_no_data(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_standup.return_value = {
            "done": [],
            "today_done": [],
            "today": [],
            "blockers": [],
        }

        result = invoke_cli(["standup"])

        assert result.exit_code == 0
        assert "nothing recorded" in result.output
        assert "nothing planned yet" in result.output
        assert "none" in result.output

    @freeze_time("2025-01-20 09:00:00")
    def test_standup_calls_manager_with_today(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_standup.return_value = {
            "done": [],
            "today_done": [],
            "today": [],
            "blockers": [],
        }

        invoke_cli(["standup"])

        cli_manager.get_standup.assert_called_once_with(datetime(2025, 1, 20, 9, 0))
