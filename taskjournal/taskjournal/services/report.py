import os
from datetime import datetime, timedelta
from typing import Optional

from jinja2 import Template

from taskjournal.config import (
    BASE_DIR,
    WEEK_SUMMARY_TEMPLATE,
    MONTH_REVIEW_TEMPLATE,
    HALF_YEAR_REVIEW_TEMPLATE,
    RETRO_TEMPLATE,
    ONE_ON_ONE_TEMPLATE,
)
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.file import (
    load_template,
    write_to_file,
    get_summary_from_daily_notes,
)
from taskjournal.services.github import GithubService
from taskjournal.services.jira import JiraService
from taskjournal.services.logger import logger
from taskjournal.services.openai import OpenAIService
from taskjournal.services.task_manager import (
    get_tasks_from_daily_notes,
    unique_tasks,
    get_unique_epics,
)
from taskjournal.services.time import (
    get_week_folder,
    get_total_time_from_daily_notes,
    get_1on1_name,
)


class ReportService:
    def __init__(
        self,
        jira_service: Optional[JiraService] = None,
        github_service: Optional[GithubService] = None,
        openai_service: Optional[OpenAIService] = None,
        task_formatter: Optional[TaskFormatter] = None,
    ) -> None:
        self.jira = jira_service or JiraService()
        self.github = github_service or GithubService()
        self.openai = openai_service or OpenAIService()
        self.task_formatter = task_formatter or TaskFormatter()

    async def create_week_report(self, today: datetime) -> None:
        week_folder = get_week_folder(BASE_DIR, today)
        report_file = os.path.join(week_folder, "WeekSummary.md")

        all_tasks = []
        total_seconds = 0
        summaries = []

        for i in range(5):  # Mon-Fri
            day = today - timedelta(days=today.weekday() - i)
            daily_file = os.path.join(
                week_folder, day.strftime("%Y-%m-%d") + "-DailyNotes.md"
            )
            if os.path.exists(daily_file):
                all_tasks.extend(get_tasks_from_daily_notes(daily_file))
                total_seconds += get_total_time_from_daily_notes(daily_file)
                summaries.append(get_summary_from_daily_notes(daily_file))

        unique_tasks_list = unique_tasks(all_tasks)
        epics = get_unique_epics(unique_tasks_list)

        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        template_content = load_template(WEEK_SUMMARY_TEMPLATE)
        template = Template(template_content)

        content = template.render(
            week_number=today.isocalendar()[1],
            total_time=f"{hours:02d}:{minutes:02d}",
            tasks=self.task_formatter.format_tasks(unique_tasks_list, with_status=True),
            epics=", ".join([f"[{e.key}]({e.link})" for e in epics]),
            summaries="\n".join(summaries),
        )

        write_to_file(report_file, content)
        logger.info(f"✅ Week report created: {report_file}")

    async def create_month_review(self, today: datetime) -> None:
        # Similar logic for month review
        month_name = today.strftime("%B")
        year = today.year
        report_file = os.path.join(BASE_DIR, str(year), f"{month_name}-Review.md")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)

        tasks = await self.jira.get_current_tasks_assigned_to_me_last_month()
        formatted_tasks = self.task_formatter.format_tasks(tasks, with_status=True)

        template_content = load_template(MONTH_REVIEW_TEMPLATE)
        template = Template(template_content)
        content = template.render(
            month=month_name,
            year=year,
            tasks=formatted_tasks,
        )

        write_to_file(report_file, content)
        logger.info(f"✅ Month review created: {report_file}")

    async def create_half_year_review(self, today: datetime) -> None:
        year = today.year
        period = "H1" if today.month <= 6 else "H2"
        report_file = os.path.join(BASE_DIR, str(year), f"{period}-Review.md")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)

        tasks = await self.jira.get_current_tasks_assigned_to_me_last_6_months()
        formatted_tasks = self.task_formatter.format_tasks(tasks, with_status=True)

        template_content = load_template(HALF_YEAR_REVIEW_TEMPLATE)
        template = Template(template_content)
        content = template.render(
            year=year,
            period=period,
            tasks=formatted_tasks,
        )

        write_to_file(report_file, content)
        logger.info(f"✅ Half year review created: {report_file}")

    def create_retro(self, today: datetime) -> None:
        week_folder = get_week_folder(BASE_DIR, today)
        report_file = os.path.join(week_folder, "Retro.md")

        template_content = load_template(RETRO_TEMPLATE)
        template = Template(template_content)
        content = template.render(date=today.strftime("%Y-%m-%d"))

        write_to_file(report_file, content)
        logger.info(f"✅ Retro file created: {report_file}")

    def create_1on1(self, today: datetime) -> None:
        week_folder = get_week_folder(BASE_DIR, today)
        report_name = get_1on1_name(today)
        report_file = os.path.join(week_folder, report_name)

        template_content = load_template(ONE_ON_ONE_TEMPLATE)
        template = Template(template_content)
        content = template.render(date=today.strftime("%Y-%m-%d"))

        write_to_file(report_file, content)
        logger.info(f"✅ 1on1 file created: {report_file}")
