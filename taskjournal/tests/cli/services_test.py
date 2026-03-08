from pytest_mock import MockerFixture

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from collections.abc import Callable
from typer.testing import Result


class TestServices:

    def test_services_jira_happy_path(
        self,
        cli_jira: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # async methods must be AsyncMock
        # given
        cli_jira.get_current_sprint_tasks_not_done_assigned_to_me = AsyncMock(
            return_value=["TASK-1"]
        )

        # when
        result = invoke_cli(["services", "jira"])

        # then
        assert result.exit_code == 0
        cli_jira.get_current_sprint_tasks_not_done_assigned_to_me.assert_awaited_once()

    def test_services_git_happy_path(
        self,
        mocker: MockerFixture,
        cli_github: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # async methods must be AsyncMock
        # given
        cli_github.get_org_commit_stats = AsyncMock(return_value=[])
        cli_github.print_commit_stats = mocker.MagicMock()

        # when
        result = invoke_cli(
            [
                "services",
                "git",
                "--contributed",
                "--stats",
            ],
        )

        # then
        assert result.exit_code == 0
        cli_github.get_org_commit_stats.assert_awaited_once()
        cli_github.print_commit_stats.assert_called_once()

    def test_services_jira_all_option(
        self,
        cli_jira: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_jira.get_current_sprint_tasks = AsyncMock(return_value=["TASK-ALL"])

        # when
        result = invoke_cli(["services", "jira", "--all"])

        # then
        assert result.exit_code == 0
        cli_jira.get_current_sprint_tasks.assert_awaited_once()

    def test_services_jira_mine_option(
        self,
        cli_jira: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_jira.get_current_sprint_tasks_all_assigned_to_me = AsyncMock(
            return_value=["TASK-MINE"]
        )

        # when
        result = invoke_cli(["services", "jira", "--mine"])

        # then
        assert result.exit_code == 0
        cli_jira.get_current_sprint_tasks_all_assigned_to_me.assert_awaited_once()

    def test_services_jira_code_midreview_and_month_options(
        self,
        cli_jira: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_jira.get_current_sprint_tasks_in_code_review = AsyncMock(
            return_value=["TASK-CODE"]
        )
        cli_jira.get_current_tasks_assigned_to_me_last_6_months = AsyncMock(
            return_value=["TASK-6M"]
        )
        cli_jira.get_current_tasks_assigned_to_me_last_month = AsyncMock(
            return_value=["TASK-1M"]
        )

        # when
        code_result = invoke_cli(["services", "jira", "--code"])
        review_result = invoke_cli(["services", "jira", "--midreview"])
        month_result = invoke_cli(["services", "jira", "--month"])

        # then
        assert code_result.exit_code == 0
        assert review_result.exit_code == 0
        assert month_result.exit_code == 0
        cli_jira.get_current_sprint_tasks_in_code_review.assert_awaited_once()
        cli_jira.get_current_tasks_assigned_to_me_last_6_months.assert_awaited_once()
        cli_jira.get_current_tasks_assigned_to_me_last_month.assert_awaited_once()

    def test_services_git_rejects_date_or_contributed_without_stats(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # when
        result = invoke_cli(["services", "git", "--date", "2025-01-01"])

        # then
        assert result.exit_code == 1
        cli_manager.github.get_org_commit_stats.assert_not_called()

    def test_services_git_invalid_date_with_stats(
        self,
        cli_github: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # when
        result = invoke_cli(["services", "git", "--stats", "--date", "bad-date"])

        # then
        assert result.exit_code == 1
        cli_github.get_org_commit_stats.assert_not_called()

    def test_services_git_stats_with_date(
        self,
        mocker: MockerFixture,
        cli_github: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        cli_github.get_org_commit_stats = AsyncMock(return_value=[{"k": "v"}])
        cli_github.print_commit_stats = mocker.MagicMock()

        # when
        result = invoke_cli(
            ["services", "git", "--stats", "--date", "2025-01-01", "--contributed"],
        )

        # then
        assert result.exit_code == 0
        cli_github.get_org_commit_stats.assert_awaited_once()
        cli_github.print_commit_stats.assert_called_once_with([{"k": "v"}])
