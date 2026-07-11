from asyncio import run
from collections.abc import Callable
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from freezegun import freeze_time
from pytest_mock import MockerFixture
from typer.testing import Result

from taskjournal.models.github import PullRequest


class TestPRCLI:

    @freeze_time("2025-01-15 10:00:00")
    def test_list_prs_empty_prints_no_prs_message(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.list_prs = AsyncMock(return_value=[])

        result = invoke_cli(["pr", "list"])

        assert result.exit_code == 0
        assert "No PRs" in result.output

    @freeze_time("2025-01-15 10:00:00")
    def test_list_prs_shows_table_with_prs(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        pr = PullRequest(
            repo="myorg/myrepo",
            number=42,
            title="Fix the bug",
            url="https://github.com/myorg/myrepo/pull/42",
            author="alice",
        )
        cli_manager.list_prs = AsyncMock(return_value=[pr])

        result = invoke_cli(["pr", "list"])

        assert result.exit_code == 0
        assert "myorg/myrepo" in result.output
        assert "Fix the bug" in result.output
        assert "alice" in result.output

    @freeze_time("2025-01-15 10:00:00")
    def test_sync_prs_none_added(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.sync_prs = AsyncMock(return_value=0)

        result = invoke_cli(["pr", "sync"])

        assert result.exit_code == 0
        assert "already" in result.output

    @freeze_time("2025-01-15 10:00:00")
    def test_sync_prs_adds_prs(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.sync_prs = AsyncMock(return_value=3)

        result = invoke_cli(["pr", "sync"])

        assert result.exit_code == 0
        assert "3" in result.output

    @freeze_time("2025-01-15 10:00:00")
    def test_sync_prs_file_not_found_logs_error(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.sync_prs = AsyncMock(
            side_effect=FileNotFoundError("No daily notes for 2025-01-15")
        )
        mock_logger = mocker.patch("taskjournal.cli.commands.pr.logger.error")

        result = invoke_cli(["pr", "sync"])

        assert result.exit_code == 0
        mock_logger.assert_called_once()
