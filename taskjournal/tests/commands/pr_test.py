from datetime import datetime

import pytest
from pytest import mark
from pytest_mock import MockerFixture
from unittest.mock import AsyncMock, MagicMock

from taskjournal.commands.pr import PRCommands
from taskjournal.models.github import PullRequest


@pytest.fixture
def pr_cmd(mocker: MockerFixture) -> PRCommands:
    github = mocker.MagicMock(name="GithubServiceMock")
    github.__aenter__ = AsyncMock(return_value=github)
    github.__aexit__ = AsyncMock(return_value=False)
    task_commands = mocker.MagicMock(name="TaskCommandsMock")
    task_manager = mocker.MagicMock(name="TaskManagerMock")
    return PRCommands(
        github=github,
        task_commands=task_commands,
        task_manager=task_manager,
    )


class TestPRCommands:

    @mark.asyncio
    async def test_list_prs_returns_prs_from_github(
        self, pr_cmd: PRCommands
    ) -> None:
        pr = PullRequest(
            repo="org/repo",
            number=1,
            title="Fix bug",
            url="https://github.com/org/repo/pull/1",
            author="bob",
        )
        pr_cmd.github.get_prs_pending_review = AsyncMock(return_value=[pr])

        result = await pr_cmd.list_prs()

        assert result == [pr]
        pr_cmd.github.get_prs_pending_review.assert_awaited_once()

    @mark.asyncio
    async def test_sync_prs_raises_when_daily_file_missing(
        self, pr_cmd: PRCommands, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "taskjournal.commands.pr.TimeService.resolve_daily_notes_file",
            return_value=("/fake/2025-01-15-DailyNotes.md", "/fake/week3"),
        )
        mocker.patch("taskjournal.commands.pr.exists", return_value=False)

        with pytest.raises(FileNotFoundError):
            await pr_cmd.sync_prs(datetime(2025, 1, 15))

    @mark.asyncio
    async def test_sync_prs_returns_zero_when_no_prs(
        self, pr_cmd: PRCommands, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "taskjournal.commands.pr.TimeService.resolve_daily_notes_file",
            return_value=("/fake/2025-01-15-DailyNotes.md", "/fake/week3"),
        )
        mocker.patch("taskjournal.commands.pr.exists", return_value=True)
        pr_cmd.github.get_prs_pending_review = AsyncMock(return_value=[])
        pr_cmd.task_manager.get_tasks_from_daily_notes.return_value = []

        result = await pr_cmd.sync_prs(datetime(2025, 1, 15))

        assert result == 0

    @mark.asyncio
    async def test_sync_prs_skips_already_existing_tasks(
        self, pr_cmd: PRCommands, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "taskjournal.commands.pr.TimeService.resolve_daily_notes_file",
            return_value=("/fake/2025-01-15-DailyNotes.md", "/fake/week3"),
        )
        mocker.patch("taskjournal.commands.pr.exists", return_value=True)
        pr = PullRequest(
            repo="org/repo",
            number=42,
            title="Fix bug",
            url="https://github.com/org/repo/pull/42",
            author="alice",
        )
        pr_cmd.github.get_prs_pending_review = AsyncMock(return_value=[pr])
        existing_task = MagicMock()
        existing_task.description = "Code review: Fix bug (org/repo#42)"
        pr_cmd.task_manager.get_tasks_from_daily_notes.return_value = [existing_task]

        result = await pr_cmd.sync_prs(datetime(2025, 1, 15))

        assert result == 0
        pr_cmd.task_commands.add_task_to_daily.assert_not_called()

    @mark.asyncio
    async def test_sync_prs_adds_new_pr_tasks(
        self, pr_cmd: PRCommands, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "taskjournal.commands.pr.TimeService.resolve_daily_notes_file",
            return_value=("/fake/2025-01-15-DailyNotes.md", "/fake/week3"),
        )
        mocker.patch("taskjournal.commands.pr.exists", return_value=True)
        pr = PullRequest(
            repo="org/repo",
            number=5,
            title="Add feature",
            url="https://github.com/org/repo/pull/5",
            author="carol",
        )
        pr_cmd.github.get_prs_pending_review = AsyncMock(return_value=[pr])
        pr_cmd.task_manager.get_tasks_from_daily_notes.return_value = []

        result = await pr_cmd.sync_prs(datetime(2025, 1, 15))

        assert result == 1
        pr_cmd.task_commands.add_task_to_daily.assert_called_once()
