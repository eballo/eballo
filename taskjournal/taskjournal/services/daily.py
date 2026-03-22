import os
from datetime import datetime, timedelta
from typing import Optional

from jinja2 import Template

from taskjournal.config import (
    DAILY_NOTES_TEMPLATE,
    DAILY_NOTES_END_TEMPLATE,
    BASE_DIR,
)
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.file import (
    load_template,
    write_to_file,
    get_lines,
)
from taskjournal.services.fireman import FiremanService
from taskjournal.services.jira import JiraService
from taskjournal.services.logger import logger
from taskjournal.services.openai import OpenAIService
from taskjournal.services.task_manager import (
    get_default_tasks,
    get_previous_pending_tasks,
    get_work_from_location,
)
from taskjournal.services.time import (
    get_daily_notes_name,
    get_week_folder,
    get_start_time,
    get_total_time_spent,
    calculate_working_hours,
)


class DailyService:
    def __init__(
        self,
        jira_service: Optional[JiraService] = None,
        openai_service: Optional[OpenAIService] = None,
        task_formatter: Optional[TaskFormatter] = None,
    ) -> None:
        self.jira = jira_service or JiraService()
        self.openai = openai_service or OpenAIService()
        self.task_formatter = task_formatter or TaskFormatter()

    def _get_daily_notes_file_path(self, date: datetime) -> str:
        week_folder = get_week_folder(BASE_DIR, date)
        os.makedirs(week_folder, exist_ok=True)
        daily_notes_name = get_daily_notes_name(date)
        return os.path.join(week_folder, daily_notes_name)

    async def create_daily_notes(
        self,
        create_datetime: datetime,
        force: bool = False,
        firefighter: bool = False,
        work_from: Optional[str] = None,
    ) -> None:
        daily_notes_file = self._get_daily_notes_file_path(create_datetime)

        if os.path.exists(daily_notes_file) and not force:
            logger.warning(f"Daily notes file already exists: {daily_notes_file}")
            return

        template_content = load_template(DAILY_NOTES_TEMPLATE)
        sprint = self.jira.get_active_sprint()
        work_from = work_from or get_work_from_location(create_datetime)

        is_fireman_week = FiremanService(create_datetime).is_fireman_week()
        firefighter = firefighter or is_fireman_week

        # Tasks logic
        tasks = get_default_tasks()
        if create_datetime.strftime("%A") == "Monday":
            logger.info("Checking for pending tasks from last week...")
            one_week_ago = create_datetime - timedelta(weeks=1)
            week_folder = get_week_folder(BASE_DIR, one_week_ago)
            pending_tasks = get_previous_pending_tasks(
                week_folder, os.path.basename(daily_notes_file)
            )
            tasks.extend(pending_tasks)
        else:
            week_folder = os.path.dirname(daily_notes_file)
            pending_tasks = get_previous_pending_tasks(
                week_folder, os.path.basename(daily_notes_file)
            )
            tasks.extend(pending_tasks)

        formatted_tasks = self.task_formatter.format_tasks(tasks)

        # Jira tasks
        jira_tasks = await self.jira.get_current_sprint_tasks_not_done_assigned_to_me()
        formatted_jira_tasks = self.task_formatter.format_tasks(jira_tasks)

        template = Template(template_content)
        content = template.render(
            sprint_name=sprint.name if sprint else "N/A",
            date=create_datetime.strftime("%Y-%m-%d"),
            start_time=create_datetime.strftime("%H:%M:%S"),
            work_from=work_from,
            tasks=formatted_tasks,
            jira_tasks=formatted_jira_tasks,
            firefighter="Yes" if firefighter else "No",
        )

        write_to_file(daily_notes_file, content)
        logger.info(f"✅ Daily notes created: {daily_notes_file}")

    def finalize_daily_notes(self, today: datetime) -> None:
        daily_notes_file = self._get_daily_notes_file_path(today)
        if not os.path.exists(daily_notes_file):
            logger.error(f"Daily notes file not found: {daily_notes_file}")
            return

        lines = get_lines(daily_notes_file)
        try:
            start_line_index, created_time = get_start_time(lines)
        except ValueError as e:
            logger.error(e)
            return

        final_time = datetime.now()
        hours, minutes = get_total_time_spent(created_time, final_time)

        template_content = load_template(DAILY_NOTES_END_TEMPLATE)
        template = Template(template_content)
        end_content = template.render(
            end_time=final_time.strftime("%H:%M:%S"),
            total_time=f"{hours:02d}:{minutes:02d}",
        )

        # Check if already finalized to avoid double entries
        for line in lines:
            if "Finalized:" in line or "End Time:" in line:
                logger.warning("Daily notes already finalized.")
                return

        write_to_file(daily_notes_file, end_content, mode="a")
        logger.info(f"✅ Daily notes finalized: {daily_notes_file}")

    def daily_time(self, today: datetime) -> None:
        daily_notes_file = self._get_daily_notes_file_path(today)
        if not os.path.exists(daily_notes_file):
            logger.error(f"Daily notes file not found: {daily_notes_file}")
            return

        created_time, elapsed_hours, finish_time = calculate_working_hours(
            daily_notes_file
        )
        if created_time and elapsed_hours and finish_time:
            logger.info(f"Start Time: {created_time.strftime('%H:%M:%S')}")
            logger.info(f"Elapsed: {elapsed_hours:.2f} hours")
            logger.info(f"Estimated Finish: {finish_time.strftime('%H:%M:%S')}")
        else:
            logger.error("Could not calculate daily time.")
