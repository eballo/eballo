from asyncio import run
from unittest.mock import AsyncMock, MagicMock, patch

from collections.abc import Callable
from freezegun import freeze_time
from typer.testing import Result

from taskjournal.constants import JIRA_MODE_ALL, JIRA_MODE_DEFAULT, JIRA_MODE_MINE


class TestServices:

    def test_services_jira_happy_path(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_manager.get_jira_tasks = AsyncMock(return_value=["TASK-1"])

        # when
        result = invoke_cli(["services", "jira"])

        # then
        assert result.exit_code == 0
        cli_manager.get_jira_tasks.assert_awaited_once_with(JIRA_MODE_DEFAULT)

    def test_services_git_happy_path(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_manager.get_github_stats = AsyncMock(return_value=[])

        # when
        with patch("taskjournal.cli.commands.services.GithubService.print_commit_stats"):
            result = invoke_cli(["services", "git", "--contributed", "--stats"])

        # then
        assert result.exit_code == 0
        cli_manager.get_github_stats.assert_awaited_once()

    def test_services_jira_all_option(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_manager.get_jira_tasks = AsyncMock(return_value=["TASK-ALL"])

        # when
        result = invoke_cli(["services", "jira", "--all"])

        # then
        assert result.exit_code == 0
        cli_manager.get_jira_tasks.assert_awaited_once_with(JIRA_MODE_ALL)

    def test_services_jira_mine_option(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_manager.get_jira_tasks = AsyncMock(return_value=["TASK-MINE"])

        # when
        result = invoke_cli(["services", "jira", "--mine"])

        # then
        assert result.exit_code == 0
        cli_manager.get_jira_tasks.assert_awaited_once_with(JIRA_MODE_MINE)

    def test_services_jira_code_midreview_and_month_options(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_manager.get_jira_tasks = AsyncMock(side_effect=[["TASK-CODE"], ["TASK-6M"], ["TASK-1M"]])

        # when
        code_result = invoke_cli(["services", "jira", "--code"])
        review_result = invoke_cli(["services", "jira", "--midreview"])
        month_result = invoke_cli(["services", "jira", "--month"])

        # then
        assert code_result.exit_code == 0
        assert review_result.exit_code == 0
        assert month_result.exit_code == 0

    def test_services_git_rejects_date_or_contributed_without_stats(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_manager.get_github_stats = AsyncMock(return_value=None)

        # when
        result = invoke_cli(["services", "git", "--date", "2025-01-01"])

        # then
        assert result.exit_code == 1
        cli_manager.get_github_stats.assert_not_awaited()

    def test_services_git_invalid_date_with_stats(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_manager.get_github_stats = AsyncMock(return_value=None)

        # when
        result = invoke_cli(["services", "git", "--stats", "--date", "bad-date"])

        # then
        assert result.exit_code == 1
        cli_manager.get_github_stats.assert_not_awaited()

    def test_services_git_stats_with_date(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_manager.get_github_stats = AsyncMock(return_value=[])

        # when
        with patch("taskjournal.cli.commands.services.GithubService.print_commit_stats"):
            result = invoke_cli(
                ["services", "git", "--stats", "--date", "2025-01-01", "--contributed"],
            )

        # then
        assert result.exit_code == 0
        cli_manager.get_github_stats.assert_awaited_once()

    @freeze_time("2025-01-15 10:00:00")
    def test_services_screentime_no_data(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_screen_time.return_value = []

        result = invoke_cli(["services", "screentime"])

        assert result.exit_code == 0
        assert "No Screen Time" in result.output

    @freeze_time("2025-01-15 10:00:00")
    def test_services_screentime_with_data(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.get_screen_time.return_value = [
            ("Safari", 3600),
            ("Xcode", 7200),
            ("Terminal", 1800),
        ]

        result = invoke_cli(["services", "screentime"])

        assert result.exit_code == 0
        assert "Safari" in result.output or "Xcode" in result.output

    @freeze_time("2025-01-15 10:00:00")
    def test_services_claude_prints_result(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.run_ai_prompt = AsyncMock(return_value="Hello from Claude!")

        result = invoke_cli(["services", "claude"])

        assert result.exit_code == 0
        assert "Hello from Claude!" in result.output
