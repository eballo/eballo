import os
from datetime import datetime, timedelta

from jinja2 import Template

from taskjournal.config import (
    TEMPLATE_FORMAT,
    DAILY_NOTES_TEMPLATE,
    BASE_DIR,
    WEEK_SUMMARY_TEMPLATE,
    RETRO_TEMPLATE,
    HALF_YEAR_REVIEW_TEMPLATE,
    MONTH_REVIEW_TEMPLATE,
    ONE_ON_ONE_TEMPLATE,
)
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.backup import BackupService
from taskjournal.services.file import FileService
from taskjournal.services.fireman import FiremanService
from taskjournal.services.github import GithubService
from taskjournal.services.jira import JiraService
from taskjournal.services.logger import logger
from taskjournal.services.openai import OpenAIService
from taskjournal.services.parser import DailyParserService
from taskjournal.services.task_manager import TaskManager
from taskjournal.services.time import TimeService
from taskjournal.services.utils import FormatUtils
from taskjournal.services.working_days import WorkingDaysService


def _apply_replacements(template: str, replacements: dict[str, str]) -> str:
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


def _to_hours_minutes(total_seconds: int) -> tuple[int, int]:
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return int(hours), int(minutes)


class CommandManager:

    def __init__(
        self,
        jira: JiraService,
        github: GithubService,
        task_formatter: TaskFormatter,
        openai: OpenAIService,
        parser: DailyParserService,
        task_manager: TaskManager,
        debug: bool = False,
    ) -> None:
        self.debug = debug
        self.jira = jira
        self.github = github
        self.task_formatter = task_formatter
        self.openai = openai
        self.parser = parser
        self.task_manager = task_manager

    @staticmethod
    def _get_week_folder(date: datetime) -> str:
        week_folder = FileService.get_week_folder(BASE_DIR, date)
        os.makedirs(week_folder, exist_ok=True)
        return week_folder

    def _get_daily_notes_file_path(self, today: datetime) -> str:
        week_folder = self._get_week_folder(today)
        daily_notes_name = TimeService.get_daily_notes_name(today)
        daily_notes_file = os.path.join(week_folder, daily_notes_name)
        return daily_notes_file

    async def create_daily_notes(
        self,
        create_datetime: datetime,
        force: bool = False,
        firefighter: bool = False,
        work_from: str | None = None,
    ) -> None:

        daily_notes_file = self._get_daily_notes_file_path(create_datetime)
        template_content = FileService.load_template(DAILY_NOTES_TEMPLATE)

        if os.path.exists(daily_notes_file) and not force:
            logger.warning(f"Daily notes file already exists: {daily_notes_file}")
            return None

        sprint = self.jira.get_active_sprint()

        folder_path = os.path.dirname(daily_notes_file)
        current_file = os.path.basename(daily_notes_file)

        # work from
        work_from = work_from if work_from else self.task_manager.get_work_from_location(create_datetime)

        # fireman logic
        is_fireman_week = FiremanService(create_datetime).is_fireman_week()
        firefighter = firefighter if firefighter else is_fireman_week

        # tasks
        default = self.task_manager.get_default_tasks()
        if create_datetime.strftime("%A") == "Monday":
            logger.info("Checking for pending tasks from last week...")
            one_week_ago = create_datetime - timedelta(weeks=1)
            week_folder = self._get_week_folder(one_week_ago)
            last_week_pending_tasks = self.task_manager.get_previous_pending_tasks(
                week_folder, current_file
            )
        else:
            last_week_pending_tasks = []

        previous_pending_tasks = self.task_manager.get_previous_pending_tasks(folder_path, current_file)
        pending = await self.jira.get_current_sprint_tasks_not_done_assigned_to_me()
        code_review = await self.jira.get_current_sprint_tasks_in_code_review()

        # validate + update status if is already reviewed
        await self.github.update_status_if_task_reviewed(code_review)

        tasks = TaskManager.unique_tasks(
            default + last_week_pending_tasks + previous_pending_tasks + pending
        )

        daily_notes_content = Template(template_content).render(
            day_name=create_datetime.strftime("%A"),
            date=create_datetime.strftime("%Y-%m-%d"),
            start_time=create_datetime.strftime("%H:%M:%S"),
            end_time="",
            time_spent="",
            work_from=work_from,
            sprint_name=sprint.name if sprint else "No active sprint",
            tasks=self.task_formatter.format_tasks(tasks, with_name=True),
            code_review_tasks=self.task_formatter.format_tasks(
                code_review,
                with_name=True,
            ),
            notes="-",
            summary="",
            firefighter=firefighter,
            firefighter_notes="-",
            extra="",
        )

        FileService.write_to_file(daily_notes_file, daily_notes_content)

        logger.debug(f"Daily Notes created successfully {daily_notes_file}")
        logger.info(
            f"Estimated time to finish {TimeService.estimated_finish_time(create_datetime)}"
        )
        return None

    def finalize_daily_notes(self, custom_date: datetime) -> None:

        daily_notes_file = self._get_daily_notes_file_path(custom_date)

        if not os.path.exists(daily_notes_file):
            logger.error(f"Daily notes file does not exist: {daily_notes_file}")
            return None

        if FileService.check_finalized_in_file(daily_notes_file):
            logger.warning(f"File '{daily_notes_file}' is already finalized.")
            return None

        if not custom_date:
            final_time = datetime.now()
        else:
            logger.warning(f"FORCE DATE - Custom date provided: {custom_date}")
            final_time = custom_date

        content = FileService.get_lines(daily_notes_file)
        created_line_index, created_time = TimeService.get_start_time(content)

        end_time = FormatUtils.wrap_with_format("End Time:")
        finalized_line = f"{end_time} {final_time.strftime('%H:%M')}\n"
        time_spent = FormatUtils.wrap_with_format("Time Spent:")

        hours, minutes = TimeService.get_total_time_spent(created_time, final_time)
        total_time_line = f"{time_spent} {int(hours):02}:{int(minutes):02}\n"

        # Remove old Finalized and Total Time Spent lines if they exist
        content = [
            line
            for line in content
            if not line.startswith(f"{end_time}")
            and not line.startswith(f"{time_spent}")
        ]

        # Insert finalized time and total time spent below the creation date
        content.insert(created_line_index + 1, finalized_line)
        content.insert(created_line_index + 2, total_time_line)
        FileService.write_lines_to_file(daily_notes_file, content)

        logger.info(f"Daily notes finalized {daily_notes_file}")
        logger.info(f"Total Time Spent: {int(hours):02}:{int(minutes):02}")

        return None

    def daily_time(self, custom_date: datetime) -> None:
        daily_notes_file = self._get_daily_notes_file_path(custom_date)
        if os.path.exists(daily_notes_file):
            self._calculate_time(daily_notes_file)
        else:
            logger.warning(f"Daily notes file does not exist: {daily_notes_file}")

    async def create_week_summary(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        summary_file = os.path.join(week_folder, f"week-summary.{TEMPLATE_FORMAT}")
        week_summary_content = FileService.load_template(WEEK_SUMMARY_TEMPLATE)

        # Get statistics
        working_days_service = WorkingDaysService(year=custom_date.year, parser=self.parser)
        stats = working_days_service.get_week_stats(custom_date, week_folder)

        # Get fireman status
        is_fireman_week = FiremanService(custom_date).is_fireman_week()

        total_hours, total_minutes = _to_hours_minutes(stats["total_time_seconds"])
        week_summary_content = _apply_replacements(
            week_summary_content,
            {
                "{{start_date}}": stats["start_date"].strftime("%Y-%m-%d"),
                "{{end_date}}": stats["end_date"].strftime("%Y-%m-%d"),
                "{{total_time}}": f" {total_hours} hours and {total_minutes} minutes",
                "{{total_worked_days}}": str(stats["total_worked_days"]),
                "{{vacation_days}}": str(stats["vacation_days"]),
                "{{days_at_office}}": str(stats["days_at_office"]),
                "{{days_at_home}}": str(stats["days_at_home"]),
                "{{is_fireman_week}}": "Yes" if is_fireman_week else "No",
            },
        )

        summary = []
        for file_name in sorted(os.listdir(week_folder)):
            if file_name.endswith(f"-DailyNotes.{TEMPLATE_FORMAT}"):
                daily_file_path = os.path.join(week_folder, file_name)
                summary.append(FileService.get_summary_from_daily_notes(daily_file_path))

        summary_ai = await self.openai.summarize(
            summary, stats=stats, is_fireman_week=is_fireman_week
        )

        week_summary_content = week_summary_content.replace("{{summary}}", summary_ai)

        FileService.write_to_file(summary_file, week_summary_content)

        logger.info(f"Week summary file created at: {summary_file}")

        return None

    async def recreate_week_summaries(
        self, start_date: datetime, end_date: datetime
    ) -> None:
        """
        Recreate all week reports from start_date to end_date (inclusive).
        It identifies each week and calls create_week_summary.
        """
        # Align start_date to Monday of its week
        current_date = start_date - timedelta(days=start_date.weekday())

        while current_date <= end_date:
            logger.info(
                f"Recreating week summary for week starting {current_date.strftime('%Y-%m-%d')}..."
            )
            await self.create_week_summary(current_date)
            current_date += timedelta(days=7)

        return None

    async def create_half_year_review(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)

        half_year_review_file = os.path.join(
            week_folder, f"half-year.{TEMPLATE_FORMAT}"
        )
        half_year_content = FileService.load_template(HALF_YEAR_REVIEW_TEMPLATE)

        # JIRA tasks and epics for the last 6 months
        tasks = await self.jira.get_current_tasks_assigned_to_me_last_6_months()
        epics = TaskManager.get_unique_epics(tasks)
        total_tasks = len(tasks)
        total_epics = len(epics)

        # GitHub contributions
        github_contributions = await self.github.get_contributions_last_6_months()

        half_year_content = _apply_replacements(
            half_year_content,
            {
                "{{total_tasks}}": str(total_tasks),
                "{{total_epics}}": str(total_epics),
                "{{github_contributions}}": str(github_contributions),
                "{{tasks}}": "\n".join(f"{task}" for task in tasks),
                "{{epics}}": "\n".join(f"{epic}" for epic in epics),
            },
        )

        FileService.write_to_file(half_year_review_file, half_year_content)

        logger.info(f"Half year review file created: {half_year_review_file}")
        # ✅ cleanup
        await self.github.close()

        return None

    async def create_month_review(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        month_review_file = os.path.join(week_folder, f"month.{TEMPLATE_FORMAT}")
        month_content = FileService.load_template(MONTH_REVIEW_TEMPLATE)

        # Get month statistics and daily summaries
        working_days_service = WorkingDaysService(year=custom_date.year, parser=self.parser, debug=self.debug)
        stats = working_days_service.get_month_stats(custom_date, BASE_DIR)

        # JIRA tasks and epics for the last month
        tasks = await self.jira.get_current_tasks_assigned_to_me_last_month()
        epics = TaskManager.get_unique_epics(tasks)
        total_tasks = len(tasks)
        total_epics = len(epics)

        # GitHub contributions
        github_contributions = await self.github.get_contributions_last_month()

        # Generate AI summary
        summary = await self.openai.summarize(
            stats["daily_summaries"],
            stats=stats,
            is_fireman_week=False,
            period="monthly",
        )

        total_hours, total_minutes = _to_hours_minutes(stats["total_time_seconds"])
        total_time_str = f"{total_hours}h {total_minutes}m"

        replacements = {
            "{{start_date}}": stats["start_date"].strftime("%Y-%m-%d"),
            "{{end_date}}": stats["end_date"].strftime("%Y-%m-%d"),
            "{{total_time}}": total_time_str,
            "{{total_worked_days}}": str(stats["total_worked_days"]),
            "{{vacation_days}}": str(stats["vacation_days"]),
            "{{days_at_office}}": str(stats["days_at_office"]),
            "{{days_at_home}}": str(stats["days_at_home"]),
            "{{total_tasks}}": str(total_tasks),
            "{{total_epics}}": str(total_epics),
            "{{github_contributions}}": str(github_contributions),
            "{{epics}}": "\n".join(f"{epic}" for epic in epics),
            "{{summary}}": summary,
        }

        for placeholder, value in replacements.items():
            month_content = month_content.replace(placeholder, value)

        FileService.write_to_file(month_review_file, month_content)
        logger.info(f"Month review file created: {month_review_file}")

        # ✅ cleanup
        await self.github.close()
        return None

    def create_retro(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        retro_file = os.path.join(week_folder, f"retro.{TEMPLATE_FORMAT}")

        if not os.path.exists(retro_file):
            template_content = FileService.load_template(RETRO_TEMPLATE)

            sprint = self.jira.get_active_sprint()
            sprint_name = sprint.name if sprint else "No active sprint"
            template_content = template_content.replace("{{sprint_name}}", sprint_name)

            FileService.write_to_file(retro_file, template_content)
            logger.info(f"Retro file ensured: {retro_file}")

        return None

    @staticmethod
    def create_one_on_one(custom_date: datetime) -> None:
        one_one_one_file_name = TimeService.get_1on1_name(custom_date)
        one_one_one_file = os.path.join(
            BASE_DIR, f"{custom_date.year}/1on1s/{one_one_one_file_name}"
        )

        if not os.path.exists(one_one_one_file):
            template_content = FileService.load_template(ONE_ON_ONE_TEMPLATE)
            FileService.write_to_file(one_one_one_file, template_content)
            logger.info(f"1on1 file ensured: {one_one_one_file}")

        return None

    @staticmethod
    def create_backup() -> None:
        backup_file = BackupService.create()
        logger.info(f"Backup created at: {backup_file}")

    @staticmethod
    def show_info(today: datetime) -> None:
        day_name = today.strftime("%A")
        week_number = today.isocalendar()[1]

        logger.info(f"📅 Today is {day_name}, {today.strftime('%Y-%m-%d')}")
        logger.info(f"🔢 We are in week {week_number}")

    @staticmethod
    def _calculate_time(daily_notes_file: str) -> None:
        started_time, elapsed_hours, finish_time = TimeService.calculate_working_hours(
            daily_notes_file
        )
        if elapsed_hours is not None and finish_time is not None:
            logger.info(f"Started time: {started_time}")
            logger.info(f"Elapsed working time: {elapsed_hours:.2f}")
            logger.info(
                f"Estimated finish time: {finish_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            logger.error("Could not calculate working hours.")
