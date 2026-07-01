from datetime import datetime

from taskjournal.constants import (
    JIRA_MODE_ALL,
    JIRA_MODE_CODE,
    JIRA_MODE_DEFAULT,
    JIRA_MODE_MIDREVIEW,
    JIRA_MODE_MINE,
    JIRA_MODE_MONTH,
)
from taskjournal.models.github import RepoCommitStat
from taskjournal.models.task import Task
from taskjournal.services.ai_service import AIService
from taskjournal.services.backup import BackupService
from taskjournal.services.github import GithubService
from taskjournal.services.jira import JiraService
from taskjournal.services.logger import logger
from taskjournal.services.time import TimeService


class AdminCommands:

    def __init__(
        self,
        backup_service: BackupService,
        time_service: TimeService,
        jira: JiraService,
        github: GithubService,
        ai_service: AIService,
    ) -> None:
        self.backup_service = backup_service
        self.time_service = time_service
        self.jira = jira
        self.github = github
        self.ai_service = ai_service

    def create_backup(self) -> None:
        backup_file = self.backup_service.create()
        logger.info(f"Backup created at: {backup_file}")

    def show_info(self, today: datetime) -> None:
        day_name = today.strftime("%A")
        week_number = today.isocalendar()[1]
        logger.info(f"📅 Today is {day_name}, {today.strftime('%Y-%m-%d')}")
        logger.info(f"🔢 We are in week {week_number}")

    async def get_jira_tasks(self, mode: str = JIRA_MODE_DEFAULT) -> list[Task]:
        if mode == JIRA_MODE_ALL:
            return await self.jira.get_current_sprint_tasks()
        if mode == JIRA_MODE_MINE:
            return await self.jira.get_current_sprint_tasks_all_assigned_to_me()
        if mode == JIRA_MODE_CODE:
            return await self.jira.get_current_sprint_tasks_in_code_review()
        if mode == JIRA_MODE_MIDREVIEW:
            return await self.jira.get_current_tasks_assigned_to_me_last_6_months()
        if mode == JIRA_MODE_MONTH:
            return await self.jira.get_current_tasks_assigned_to_me_last_month()
        return await self.jira.get_current_sprint_tasks_not_done_assigned_to_me()

    async def get_github_stats(
        self,
        since_date: datetime | None,
        only_contributed: bool,
        org_name: str,
    ) -> list[RepoCommitStat] | None:
        self.github.org_name = org_name
        async with self.github:
            return await self.github.get_org_commit_stats(
                since_date=since_date,
                only_contributed=only_contributed,
            )

    async def run_ai_prompt(self, prompt: str) -> str:
        return await self.ai_service.summarize([prompt])
