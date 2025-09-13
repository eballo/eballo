import os
from dataclasses import dataclass
from datetime import datetime

from taskjournal.config import (
    TEMPLATE_FORMAT,
    DAILY_NOTES_TEMPLATE,
    BASE_DIR,
    WEEK_SUMMARY_TEMPLATE,
    RETRO_TEMPLATE,
    HALF_YEAR_REVIEW_TEMPLATE,
    MONTH_REVIEW_TEMPLATE,
)
from taskjournal.models.task import Status
from taskjournal.repositories.file_writer import FileWriter
from taskjournal.services.backup import create_backup
from taskjournal.services.file import (
    load_template,
    check_finalized_in_file,
    write_to_file,
    write_lines_to_file,
    get_lines,
    get_week_folder,
)
from taskjournal.services.github import GithubService
from taskjournal.services.jira import JiraService
from taskjournal.services.logger import logger
from taskjournal.services.task_manager import (
    get_default_tasks,
    get_tasks_from_daily_notes,
    get_previous_pending_tasks,
    unique_tasks,
    get_unique_epics,
)
from taskjournal.services.time import (
    get_total_time_from_daily_notes,
    estimated_finish_time,
    get_start_time,
    calculate_working_hours,
    get_daily_notes_name,
)
from taskjournal.services.utils import wrap_with_format


@dataclass
class CommandManager:

    def __init__(self):
        self.jira = JiraService()
        self.github = GithubService()
        self.file_writer = FileWriter()

    @staticmethod
    def _get_week_folder(today: datetime) -> str:
        week_folder = get_week_folder(BASE_DIR, today)
        os.makedirs(week_folder, exist_ok=True)
        return week_folder

    def _get_daily_notes_file_path(self, today: datetime) -> str:
        week_folder = self._get_week_folder(today)
        daily_notes_name = get_daily_notes_name(today)
        daily_notes_file = os.path.join(week_folder, daily_notes_name)
        return daily_notes_file

    async def create_daily_notes(
        self,
        create_datetime: datetime,
        force: bool = False,
    ) -> None:

        daily_notes_file = self._get_daily_notes_file_path(create_datetime)
        template_content = load_template(DAILY_NOTES_TEMPLATE)

        if os.path.exists(daily_notes_file) and not force:
            logger.warning(f"Daily notes file already exists: {daily_notes_file}")
            return None

        creation_date_str = create_datetime.strftime("%Y-%m-%d")
        creation_time = create_datetime.strftime("%H:%M:%S")
        sprint = self.jira.get_active_sprint()

        daily_notes_content = template_content.replace("{{date}}", creation_date_str)
        daily_notes_content = daily_notes_content.replace("{{time}}", creation_time)
        sprint_name = sprint.name if sprint else "No active sprint"
        daily_notes_content = daily_notes_content.replace(
            "{{sprint_name}}", sprint_name
        )

        # Get tasks: unfinished tasks + default tasks
        default_tasks = get_default_tasks()
        pending_jtasks = (
            await self.jira.get_current_sprint_tasks_not_done_assigned_to_me()
        )
        code_review_jtasks = await self.jira.get_current_sprint_tasks_in_code_review()

        folder_path = os.path.dirname(daily_notes_file)
        current_file = os.path.basename(daily_notes_file)
        previous_pending_tasks = get_previous_pending_tasks(folder_path, current_file)

        tasks = unique_tasks(default_tasks + previous_pending_tasks + pending_jtasks)

        daily_notes_content = self.file_writer.format_content(
            "{{tasks}}", daily_notes_content, tasks, with_status=False
        )
        daily_notes_content = self.file_writer.format_content(
            "{{code_review_tasks}}",
            daily_notes_content,
            code_review_jtasks,
            with_name=True,
        )

        write_to_file(daily_notes_file, daily_notes_content)

        logger.debug(f"Daily Notes created successfully {daily_notes_file}")
        logger.info(
            f"Estimated time to finish {estimated_finish_time(create_datetime)}"
        )
        return None

    def finalize_daily_notes(self, custom_date: datetime) -> None:

        daily_notes_file = self._get_daily_notes_file_path(custom_date)

        if not os.path.exists(daily_notes_file):
            logger.error(f"Daily notes file does not exist: {daily_notes_file}")
            return None

        if check_finalized_in_file(daily_notes_file):
            logger.warning(f"File '{daily_notes_file}' is already finalized.")
            return None

        if not custom_date:
            final_time = datetime.now()
        else:
            logger.warning(f"FORCE DATE - Custom date provided: {custom_date}")
            final_time = custom_date

        content = get_lines(daily_notes_file)
        created_line_index, created_time = get_start_time(content)

        # Calculate finalized time and total time spent
        total_time_spent = final_time - created_time
        end_time = wrap_with_format("End Time:")
        finalized_line = f"{end_time} {final_time.strftime('%H:%M')}\n"

        # Properly format total_time_spent
        hours, remainder = divmod(total_time_spent.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        time_spent = wrap_with_format("Time Spent:")
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
        write_lines_to_file(daily_notes_file, content)

        logger.info(f"Daily notes finalized {daily_notes_file}")
        logger.info(f"Total Time Spent: {int(hours):02}:{int(minutes):02}")

        return None

    def daily_time(self, custom_date) -> None:
        daily_notes_file = self._get_daily_notes_file_path(custom_date)
        if os.path.exists(daily_notes_file):
            self._calculate_time(daily_notes_file)
        else:
            logger.warning(f"Daily notes file does not exist: {daily_notes_file}")

    def create_week_summary(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        summary_file = os.path.join(week_folder, f"week-summary.{TEMPLATE_FORMAT}")
        week_summary_content = load_template(WEEK_SUMMARY_TEMPLATE)

        done_tasks = []
        pending_tasks = []
        total_time_seconds = 0

        for file_name in sorted(os.listdir(week_folder)):
            if file_name.endswith(f"-DailyNotes.{TEMPLATE_FORMAT}"):
                daily_file_path = os.path.join(week_folder, file_name)
                tasks = get_tasks_from_daily_notes(daily_file_path)
                daily_done = [task for task in tasks if task.status == Status.DONE]
                daily_pending = [task for task in tasks if task.status == Status.TODO]
                daily_time = get_total_time_from_daily_notes(
                    daily_file_path
                )  # Extract total time from daily notes

                done_tasks.extend(daily_done)
                pending_tasks.extend(daily_pending)
                total_time_seconds += daily_time

        # Remove pending tasks that have been completed
        pending_tasks = [task for task in pending_tasks if task not in done_tasks]

        # Calculate total hours and minutes for the week
        total_hours, remainder = divmod(total_time_seconds, 3600)
        total_minutes, _ = divmod(remainder, 60)

        week_summary_content = week_summary_content.replace(
            "{{total_time}}", f" {total_hours} hours and {total_minutes} minutes"
        )
        week_summary_content = week_summary_content.replace(
            "{{done_tasks}}", "\n".join(f"{task}" for task in done_tasks)
        )
        week_summary_content = week_summary_content.replace(
            "{{pending_tasks}}", "\n".join(f"{task}" for task in pending_tasks)
        )
        week_summary_content = week_summary_content.replace(
            "{{summary}}", "\nWrite your weekly summary here...\n"
        )

        write_to_file(summary_file, week_summary_content)

        logger.info(f"Week summary file created at: {summary_file}")

        return None

    async def create_half_year_review(self, custom_date) -> None:
        week_folder = self._get_week_folder(custom_date)

        half_year_review_file = os.path.join(
            week_folder, f"half-year.{TEMPLATE_FORMAT}"
        )
        half_year_content = load_template(HALF_YEAR_REVIEW_TEMPLATE)

        # JIRA tasks and epics for the last 6 months
        tasks = await self.jira.get_current_tasks_assigned_to_me_last_6_months()
        epics = get_unique_epics(tasks)
        total_tasks = len(tasks)
        total_epics = len(epics)

        # GitHub contributions
        github_contributions = self.github.get_contributions_last_6_months()

        half_year_content = half_year_content.replace(
            "{{total_tasks}}", f"{total_tasks}"
        )
        half_year_content = half_year_content.replace(
            "{{total_epics}}", f"{total_epics}"
        )
        half_year_content = half_year_content.replace(
            "{{github_contributions}}", f"{github_contributions}"
        )

        half_year_content = half_year_content.replace(
            "{{tasks}}", "\n".join(f"{task}" for task in tasks)
        )

        half_year_content = half_year_content.replace(
            "{{epics}}", "\n".join(f"{epic}" for epic in epics)
        )

        write_to_file(half_year_review_file, half_year_content)

        logger.info(f"Half year review file created: {half_year_review_file}")

        return None

    async def create_month_review(self, custom_date) -> None:
        week_folder = self._get_week_folder(custom_date)

        half_year_review_file = os.path.join(week_folder, f"month.{TEMPLATE_FORMAT}")
        half_year_content = load_template(MONTH_REVIEW_TEMPLATE)

        # JIRA tasks and epics for the last month
        tasks = await self.jira.get_current_tasks_assigned_to_me_last_month()
        epics = get_unique_epics(tasks)
        total_tasks = len(tasks)
        total_epics = len(epics)

        # GitHub contributions
        github_contributions = self.github.get_contributions_last_month()

        half_year_content = half_year_content.replace(
            "{{total_tasks}}", f"{total_tasks}"
        )
        half_year_content = half_year_content.replace(
            "{{total_epics}}", f"{total_epics}"
        )
        half_year_content = half_year_content.replace(
            "{{github_contributions}}", f"{github_contributions}"
        )

        half_year_content = half_year_content.replace(
            "{{tasks}}", "\n".join(f"{task}" for task in tasks)
        )

        half_year_content = half_year_content.replace(
            "{{epics}}", "\n".join(f"{epic}" for epic in epics)
        )

        write_to_file(half_year_review_file, half_year_content)

        logger.info(f"Month review file created: {half_year_review_file}")

        return None

    def create_retro(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        retro_file = os.path.join(week_folder, f"retro.{TEMPLATE_FORMAT}")

        if not os.path.exists(retro_file):
            template_content = load_template(RETRO_TEMPLATE)

            sprint = self.jira.get_active_sprint()
            sprint_name = sprint.name if sprint else "No active sprint"
            template_content = template_content.replace("{{sprint_name}}", sprint_name)

            write_to_file(retro_file, template_content)
            logger.info(f"Retro file ensured: {retro_file}")

        return None

    def create_backup(self) -> None:
        backup_file = create_backup()
        logger.info(f"Backup created at: {backup_file}")

    def _calculate_time(self, daily_notes_file: str) -> None:
        started_time, elapsed_hours, finish_time = calculate_working_hours(
            daily_notes_file
        )
        if elapsed_hours is not None:
            logger.info(f"Started time: {started_time}")
            logger.info(f"Elapsed working time: {elapsed_hours:.2f}")
            logger.info(
                f"Estimated finish time: {finish_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            logger.error("Could not calculate working hours.")
