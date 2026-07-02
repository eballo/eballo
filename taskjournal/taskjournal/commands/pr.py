from datetime import datetime
from os.path import exists

from taskjournal.commands.tasks import TaskCommands
from taskjournal.models.github import PullRequest
from taskjournal.models.task import Task
from taskjournal.services.integrations.github import GithubService
from taskjournal.services.logger import console, logger
from taskjournal.services.task_manager import TaskManager
from taskjournal.services.time import TimeService


class PRCommands:

    def __init__(
        self,
        github: GithubService,
        task_commands: TaskCommands,
        task_manager: TaskManager,
    ) -> None:
        self.github = github
        self.task_commands = task_commands
        self.task_manager = task_manager

    async def list_prs(self) -> list[PullRequest]:
        async with self.github:
            return await self.github.get_prs_pending_review()

    async def sync_prs(self, date: datetime) -> int:
        daily_file, _ = TimeService.resolve_daily_notes_file(date)
        if not exists(daily_file):
            raise FileNotFoundError(f"No daily notes for {date.strftime('%Y-%m-%d')}")

        async with self.github:
            prs = await self.github.get_prs_pending_review()

        if not prs:
            return 0

        existing_tasks = self.task_manager.get_tasks_from_daily_notes(daily_file)
        existing_descs = {t.description.lower() for t in existing_tasks}

        added = 0
        for pr in prs:
            description = f"Code review: {pr.title} ({pr.repo}#{pr.number})"
            if description.lower() not in existing_descs:
                self.task_commands.add_task_to_daily(date, description)
                console.print(f"  [green]+[/green] {description}")
                added += 1

        return added
