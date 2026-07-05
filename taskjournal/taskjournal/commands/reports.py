from datetime import datetime, timedelta
from os import makedirs, listdir
from os.path import exists, join
from pathlib import Path
from re import compile as re_compile, Pattern

from jinja2 import Template

from taskjournal.config import (
    TEMPLATE_FORMAT,
    BASE_DIR,
    WEEK_SUMMARY_TEMPLATE,
    RETRO_TEMPLATE,
    HALF_YEAR_REVIEW_TEMPLATE,
    MONTH_REVIEW_TEMPLATE,
    QUARTER_REVIEW_TEMPLATE,
    YEAR_REVIEW_TEMPLATE,
    ONE_ON_ONE_TEMPLATE,
)
from taskjournal.services.ai.base import AIService
from taskjournal.services.file import FileService
from taskjournal.services.calendar.fireman import FiremanService
from taskjournal.services.integrations.github import GithubService
from taskjournal.services.integrations.jira import JiraService
from taskjournal.services.logger import console, logger
from taskjournal.services.parser import DailyParserService
from taskjournal.services.task_manager import TaskManager
from taskjournal.services.time import TimeService
from taskjournal.services.calendar.working_days import WorkingDaysService
from taskjournal.services.utils import FormatUtils


class ReportCommands:

    def __init__(
        self,
        jira: JiraService,
        github: GithubService,
        ai_service: AIService,
        parser: DailyParserService,
        file_service: FileService,
        time_service: TimeService,
        debug: bool = False,
    ) -> None:
        self.debug = debug
        self.jira = jira
        self.github = github
        self.ai_service = ai_service
        self.parser = parser
        self.file_service = file_service
        self.time_service = time_service

    def _get_week_folder(self, date: datetime) -> str:
        week_folder = self.file_service.get_week_folder(BASE_DIR, date)
        makedirs(week_folder, exist_ok=True)
        return week_folder

    def _note_issues(self, file_path: str) -> list[str]:
        issues: list[str] = []
        try:
            lines = self.file_service.get_lines(file_path)
            self.time_service.get_start_time(lines)
        except (ValueError, FileNotFoundError):
            issues.append("missing start time")
        if not self.file_service.check_finalized_in_file(file_path):
            issues.append("missing end time")
        note = self.parser.parse(file_path)
        if note and not note.time_spent.strip():
            issues.append("missing time spent")
        if note and not any(line.strip() for line in note.summary):
            issues.append("missing summary")
        return issues

    def _warn_incomplete_week_notes(self, week_date: datetime, week_folder: str) -> None:
        start_of_week = week_date - timedelta(days=week_date.weekday())
        incomplete: list[str] = []

        for i in range(5):
            day = start_of_week + timedelta(days=i)
            daily_file = join(week_folder, self.time_service.get_daily_notes_name(day))
            if not exists(daily_file):
                continue
            issues = self._note_issues(daily_file)
            if issues:
                incomplete.append(f"{day.strftime('%Y-%m-%d')}: {', '.join(issues)}")

        if incomplete:
            logger.warning("Week report generated with incomplete notes:")
            for line in incomplete:
                logger.warning(f"  ⚠  {line}")

    async def create_week_summary(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        summary_file = join(week_folder, f"week-summary.{TEMPLATE_FORMAT}")
        week_summary_content = self.file_service.load_template(WEEK_SUMMARY_TEMPLATE)

        self._warn_incomplete_week_notes(custom_date, week_folder)

        working_days_service = WorkingDaysService(year=custom_date.year, parser=self.parser)
        stats = working_days_service.get_week_stats(custom_date, week_folder)

        is_fireman_week = FiremanService(custom_date).is_fireman_week()
        total_hours, total_minutes = self.time_service.seconds_to_hours_minutes(stats["total_time_seconds"])

        summary = []
        for file_name in sorted(listdir(week_folder)):
            if file_name.endswith(f"-DailyNotes.{TEMPLATE_FORMAT}"):
                daily_file_path = join(week_folder, file_name)
                summary.append(self.file_service.get_summary_from_daily_notes(daily_file_path))

        summary_ai = await self.ai_service.summarize(summary, stats=stats, is_fireman_week=is_fireman_week)

        week_summary_content = Template(week_summary_content).render(
            start_date=stats["start_date"].strftime("%Y-%m-%d"),
            end_date=stats["end_date"].strftime("%Y-%m-%d"),
            total_time=f" {total_hours} hours and {total_minutes} minutes",
            total_worked_days=str(stats["total_worked_days"]),
            vacation_days=str(stats["vacation_days"]),
            days_at_office=str(stats["days_at_office"]),
            days_at_home=str(stats["days_at_home"]),
            is_fireman_week="Yes" if is_fireman_week else "No",
            summary=summary_ai,
        )

        self.file_service.write_to_file(summary_file, week_summary_content)
        console.print(f"[green]✓[/green] Week summary created: {summary_file}")

    async def recreate_week_summaries(self, start_date: datetime, end_date: datetime) -> None:
        current_date = start_date - timedelta(days=start_date.weekday())
        while current_date <= end_date:
            console.print(f"  Recreating week summary for week starting {current_date.strftime('%Y-%m-%d')}...")
            await self.create_week_summary(current_date)
            current_date += timedelta(days=7)

    async def create_half_year_review(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        half_year_review_file = join(week_folder, f"half-year.{TEMPLATE_FORMAT}")
        half_year_content = self.file_service.load_template(HALF_YEAR_REVIEW_TEMPLATE)

        tasks = await self.jira.get_current_tasks_assigned_to_me_last_6_months()
        epics = TaskManager.get_unique_epics(tasks)

        async with self.github:
            github_contributions = await self.github.get_contributions_last_6_months()

        half_year_content = Template(half_year_content).render(
            total_tasks=str(len(tasks)),
            total_epics=str(len(epics)),
            github_contributions=str(github_contributions),
            tasks="\n".join(f"{task}" for task in tasks),
            epics="\n".join(f"{epic}" for epic in epics),
        )

        self.file_service.write_to_file(half_year_review_file, half_year_content)
        console.print(f"[green]✓[/green] Half year review created: {half_year_review_file}")

    async def create_month_review(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        month_review_file = join(week_folder, f"month.{TEMPLATE_FORMAT}")
        month_content = self.file_service.load_template(MONTH_REVIEW_TEMPLATE)

        working_days_service = WorkingDaysService(year=custom_date.year, parser=self.parser, debug=self.debug)
        stats = working_days_service.get_month_stats(custom_date, str(BASE_DIR))

        tasks = await self.jira.get_current_tasks_assigned_to_me_last_month()
        epics = TaskManager.get_unique_epics(tasks)

        async with self.github:
            github_contributions = await self.github.get_contributions_last_month()

        summary = await self.ai_service.summarize(
            stats["daily_summaries"], stats=stats, is_fireman_week=False, period="monthly"
        )

        total_hours, total_minutes = self.time_service.seconds_to_hours_minutes(stats["total_time_seconds"])
        total_time_str = f"{total_hours}h {total_minutes}m"

        month_content = Template(month_content).render(
            start_date=stats["start_date"].strftime("%Y-%m-%d"),
            end_date=stats["end_date"].strftime("%Y-%m-%d"),
            total_time=total_time_str,
            total_worked_days=str(stats["total_worked_days"]),
            vacation_days=str(stats["vacation_days"]),
            days_at_office=str(stats["days_at_office"]),
            days_at_home=str(stats["days_at_home"]),
            total_tasks=str(len(tasks)),
            total_epics=str(len(epics)),
            github_contributions=str(github_contributions),
            epics="\n".join(f"{epic}" for epic in epics),
            summary=summary,
        )

        self.file_service.write_to_file(month_review_file, month_content)
        console.print(f"[green]✓[/green] Month review created: {month_review_file}")

    async def create_quarter_review(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        quarter_review_file = join(week_folder, f"quarter.{TEMPLATE_FORMAT}")
        quarter_content = self.file_service.load_template(QUARTER_REVIEW_TEMPLATE)

        working_days_service = WorkingDaysService(year=custom_date.year, parser=self.parser, debug=self.debug)
        stats = working_days_service.get_quarter_stats(custom_date, str(BASE_DIR))

        tasks = await self.jira.get_current_tasks_assigned_to_me_last_quarter()
        epics = TaskManager.get_unique_epics(tasks)

        async with self.github:
            github_contributions = await self.github.get_contributions_last_quarter()

        summary = await self.ai_service.summarize(
            stats["daily_summaries"], stats=stats, is_fireman_week=False, period="quarterly"
        )

        total_hours, total_minutes = self.time_service.seconds_to_hours_minutes(stats["total_time_seconds"])
        total_time_str = f"{total_hours}h {total_minutes}m"

        quarter_content = Template(quarter_content).render(
            quarter_num=str(stats["quarter_num"]),
            year=str(stats["year"]),
            start_date=stats["start_date"].strftime("%Y-%m-%d"),
            end_date=stats["end_date"].strftime("%Y-%m-%d"),
            total_time=total_time_str,
            total_worked_days=str(stats["total_worked_days"]),
            vacation_days=str(stats["vacation_days"]),
            days_at_office=str(stats["days_at_office"]),
            days_at_home=str(stats["days_at_home"]),
            total_tasks=str(len(tasks)),
            total_epics=str(len(epics)),
            github_contributions=github_contributions,
            epics="\n".join(f"{epic}" for epic in epics),
            summary=summary,
        )

        self.file_service.write_to_file(quarter_review_file, quarter_content)
        console.print(f"[green]✓[/green] Quarter review created: {quarter_review_file}")

    async def create_year_review(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        year_review_file = join(week_folder, f"year.{TEMPLATE_FORMAT}")
        year_content = self.file_service.load_template(YEAR_REVIEW_TEMPLATE)

        year = custom_date.year
        working_days_service = WorkingDaysService(year=year, parser=self.parser, debug=self.debug)
        stats = working_days_service.get_year_stats(year, str(BASE_DIR))

        tasks = await self.jira.get_current_tasks_assigned_to_me_last_year()
        epics = TaskManager.get_unique_epics(tasks)

        async with self.github:
            github_contributions = await self.github.get_contributions_last_year()

        summary = await self.ai_service.summarize(
            stats["daily_summaries"], stats=stats, is_fireman_week=False, period="yearly"
        )

        total_hours, total_minutes = self.time_service.seconds_to_hours_minutes(stats["total_time_seconds"])
        total_time_str = f"{total_hours}h {total_minutes}m"

        year_content = Template(year_content).render(
            year=str(year),
            start_date=stats["start_date"].strftime("%Y-%m-%d"),
            end_date=stats["end_date"].strftime("%Y-%m-%d"),
            total_time=total_time_str,
            total_worked_days=str(stats["total_worked_days"]),
            vacation_days=str(stats["vacation_days"]),
            days_at_office=str(stats["days_at_office"]),
            days_at_home=str(stats["days_at_home"]),
            total_tasks=str(len(tasks)),
            total_epics=str(len(epics)),
            github_contributions=github_contributions,
            epics="\n".join(f"{epic}" for epic in epics),
            summary=summary,
        )

        self.file_service.write_to_file(year_review_file, year_content)
        console.print(f"[green]✓[/green] Year review created: {year_review_file}")

    def compare_periods(self, period: str, year: int) -> list[dict[str, object]]:
        """Return stats for each month or quarter in the given year for side-by-side display."""
        working_days_service = WorkingDaysService(year=year, parser=self.parser, debug=self.debug)
        results: list[dict[str, object]] = []

        if period == "quarter":
            for q in range(1, 5):
                anchor = datetime(year, (q - 1) * 3 + 1, 15)
                stats = working_days_service.get_quarter_stats(anchor, str(BASE_DIR))
                results.append({
                    "label": f"Q{q} {year}",
                    "total_worked_days": stats["total_worked_days"],
                    "vacation_days": stats["vacation_days"],
                    "days_at_office": stats["days_at_office"],
                    "days_at_home": stats["days_at_home"],
                    "total_time_seconds": stats["total_time_seconds"],
                })
        else:
            for month in range(1, 13):
                anchor = datetime(year, month, 15)
                stats = working_days_service.get_month_stats(anchor, str(BASE_DIR))
                results.append({
                    "label": anchor.strftime("%b %Y"),
                    "total_worked_days": stats["total_worked_days"],
                    "vacation_days": stats["vacation_days"],
                    "days_at_office": stats["days_at_office"],
                    "days_at_home": stats["days_at_home"],
                    "total_time_seconds": stats["total_time_seconds"],
                })

        return results

    def create_retro(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        retro_file = join(week_folder, f"retro.{TEMPLATE_FORMAT}")

        if not exists(retro_file):
            template_content = self.file_service.load_template(RETRO_TEMPLATE)
            sprint = self.jira.get_active_sprint()
            sprint_name = sprint.name if sprint else "No active sprint"
            template_content = Template(template_content).render(sprint_name=sprint_name)
            self.file_service.write_to_file(retro_file, template_content)
            console.print(f"[green]✓[/green] Retro file created: {retro_file}")

    def create_one_on_one(self, custom_date: datetime, person_name: str = "") -> None:
        one_one_one_file_name = self.time_service.get_1on1_name(custom_date)
        one_one_one_file = join(BASE_DIR, f"{custom_date.year}/1on1s/{one_one_one_file_name}")

        if not exists(one_one_one_file):
            makedirs(str(Path(one_one_one_file).parent), exist_ok=True)
            template_content = self.file_service.load_template(ONE_ON_ONE_TEMPLATE)
            rendered = Template(template_content).render(
                date=custom_date.strftime("%Y-%m-%d"),
                person_name=person_name,
            )
            self.file_service.write_to_file(one_one_one_file, rendered)
            console.print(f"[green]✓[/green] 1on1 file created: {one_one_one_file}")

    def add_topic_to_one_on_one(self, date: datetime, topic: str) -> None:
        self.create_one_on_one(date)
        file_path = join(str(BASE_DIR), f"{date.year}/1on1s/{self.time_service.get_1on1_name(date)}")

        lines = self.file_service.get_lines(file_path)
        bullet_rx: Pattern[str] = re_compile(r"^-\s+")

        in_proposal = False
        last_bullet_idx = -1
        section_header_idx = -1

        for i, raw in enumerate(lines):
            stripped = raw.strip()
            if stripped.startswith("#"):
                in_proposal = "Proposal" in stripped or "topic" in stripped.lower()
                if in_proposal:
                    section_header_idx = i
                elif in_proposal:
                    in_proposal = False
            elif in_proposal and bullet_rx.match(stripped):
                last_bullet_idx = i

        insert_at = last_bullet_idx if last_bullet_idx != -1 else section_header_idx
        if insert_at == -1:
            raise ValueError("'Proposal topics' section not found in 1on1 file.")

        lines.insert(insert_at + 1, f"- {topic}\n")
        self.file_service.write_lines_to_file(file_path, lines)
        console.print(f"[green]✓[/green] Topic added: {topic}")
