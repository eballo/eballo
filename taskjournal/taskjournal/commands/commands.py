from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.backup import create_backup
from taskjournal.services.daily import DailyService
from taskjournal.services.github import GithubService
from taskjournal.services.jira import JiraService
from taskjournal.services.openai import OpenAIService
from taskjournal.services.report import ReportService


@dataclass
class CommandManager:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self.jira = JiraService()
        self.github = GithubService()
        self.task_formatter = TaskFormatter()
        self.openai = OpenAIService()

        # New services
        self.daily_service = DailyService(
            jira_service=self.jira,
            openai_service=self.openai,
            task_formatter=self.task_formatter,
        )
        self.report_service = ReportService(
            jira_service=self.jira,
            github_service=self.github,
            openai_service=self.openai,
            task_formatter=self.task_formatter,
        )

    async def create_daily_notes(
        self,
        create_datetime: datetime,
        force: bool = False,
        firefighter: bool = False,
        work_from: Optional[str] = None,
    ) -> None:
        await self.daily_service.create_daily_notes(
            create_datetime, force, firefighter, work_from
        )

    def finalize_daily_notes(self, today: datetime) -> None:
        self.daily_service.finalize_daily_notes(today)

    def daily_time(self, today: datetime) -> None:
        self.daily_service.daily_time(today)

    async def create_week_summary(self, today: datetime) -> None:
        await self.report_service.create_week_report(today)

    async def create_half_year_review(self, today: datetime) -> None:
        await self.report_service.create_half_year_review(today)

    async def create_month_review(self, today: datetime) -> None:
        await self.report_service.create_month_review(today)

    def create_retro(self, today: datetime) -> None:
        self.report_service.create_retro(today)

    def create_one_on_one(self, today: datetime) -> None:
        self.report_service.create_1on1(today)

    def create_backup(self) -> None:
        create_backup()
