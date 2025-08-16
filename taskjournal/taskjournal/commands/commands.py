import os
from datetime import datetime

from taskjournal.models.task import Status
from taskjournal.repositories.file_writer import FileWriter
from taskjournal.services.file import (
    load_template,
    check_finalized_in_file,
    write_to_file,
    write_lines_to_file,
    get_lines,
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
)


def create_daily_notes_file(
    file_path: str, template_path: str, create_datetime: datetime
) -> datetime:
    """
    Create a daily file using a template and adding a creation timestamp.

    Args:
        file_path (str): The path for the new daily notes file.
        template_path (str): The path to the template file.
    """

    # Load template and add timestamp
    template_content = load_template(template_path)

    creation_date_str = create_datetime.strftime("%Y-%m-%d")
    creation_time = create_datetime.strftime("%H:%M:%S")
    sprint = JiraService().get_active_sprint()

    daily_notes_content = template_content.replace("{{date}}", creation_date_str)
    daily_notes_content = daily_notes_content.replace("{{time}}", creation_time)
    sprint_name = sprint.name if sprint else "No active sprint"
    daily_notes_content = daily_notes_content.replace("{{sprint_name}}", sprint_name)

    # Get tasks: unfinished tasks + default tasks
    default_tasks = get_default_tasks()
    pending_jira_tasks = (
        JiraService().get_current_sprint_tasks_not_done_assigned_to_me()
    )

    code_review_tasks = JiraService().get_current_sprint_tasks_in_code_review()

    folder_path = os.path.dirname(file_path)
    current_file = os.path.basename(file_path)
    previous_pending_tasks = get_previous_pending_tasks(folder_path, current_file)

    tasks = unique_tasks(default_tasks + previous_pending_tasks + pending_jira_tasks)
    daily_notes_content = FileWriter.format_content(
        "{{tasks}}", daily_notes_content, tasks, with_status=False
    )
    daily_notes_content = FileWriter.format_content(
        "{{code_review_tasks}}", daily_notes_content, code_review_tasks, with_name=True
    )

    write_to_file(file_path, daily_notes_content)

    return estimated_finish_time(create_datetime)


def finalize_daily_notes(file_path: str, custom_date: datetime | None) -> None:
    """Add a final timestamp to the daily notes file and calculate total time spent."""

    if check_finalized_in_file(file_path) and not custom_date:
        logger.info(f"File '{file_path}' is already finalized.")
        return

    if not custom_date:
        final_time = datetime.now()
    else:
        logger.info(f"Custom date provided: {custom_date}")
        final_time = custom_date

    content = get_lines(file_path)
    created_line_index, created_time = get_start_time(content)

    # Calculate finalized time and total time spent
    total_time_spent = final_time - created_time
    finalized_line = f" End Time: {final_time.strftime('%H:%M')}\n"

    # Properly format total_time_spent
    hours, remainder = divmod(total_time_spent.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    total_time_line = f" Time Spent: {int(hours):02}:{int(minutes):02}\n"

    # Remove old Finalized and Total Time Spent lines if they exist
    content = [
        line
        for line in content
        if not line.startswith(" End Time:") and not line.startswith(" Time Spent:")
    ]

    # Insert finalized time and total time spent below the creation date
    content.insert(created_line_index + 1, finalized_line)
    content.insert(created_line_index + 2, total_time_line)
    write_lines_to_file(file_path, content)

    logger.info(f"Daily notes finalized with timestamp: {file_path}")
    logger.info(f"Time Spent: {int(hours):02}:{int(minutes):02}")


def create_week_summary(week_folder: str, template_path: str) -> None:
    """Create a week summary file."""
    summary_file = os.path.join(week_folder, "week-summary.txt")
    week_summary_content = load_template(template_path)
    done_tasks = []
    pending_tasks = []
    total_time_seconds = 0

    for file_name in sorted(os.listdir(week_folder)):
        if file_name.endswith("-DailyNotes.txt"):
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


def create_half_year_review(week_folder: str, template_path: str) -> None:
    half_year_review_file = os.path.join(week_folder, "half-year.txt")
    half_year_content = load_template(template_path)

    # JIRA tasks and epics for the last 6 months
    tasks = JiraService().get_current_tasks_assigned_to_me_last_6_months()
    epics = get_unique_epics(tasks)
    total_tasks = len(tasks)
    total_epics = len(epics)

    # GitHub contributions
    git_service = GithubService()
    github_contributions = git_service.get_contributions_last_6_months()

    half_year_content = half_year_content.replace("{{total_tasks}}", f"{total_tasks}")
    half_year_content = half_year_content.replace("{{total_epics}}", f"{total_epics}")
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


def create_retro_file(week_folder: str, template_path: str) -> str:
    """Create a retro file using a template."""
    retro_file = os.path.join(week_folder, "retro.txt")

    if not os.path.exists(retro_file):
        template_content = load_template(template_path)

        sprint = JiraService().get_active_sprint()
        sprint_name = sprint.name if sprint else "No active sprint"
        template_content = template_content.replace("{{sprint_name}}", sprint_name)

        write_to_file(retro_file, template_content)

    return retro_file


def calculate_time(daily_notes_file: str) -> None:
    started_time, elapsed_hours, finish_time = calculate_working_hours(daily_notes_file)
    if elapsed_hours is not None:
        logger.info(f"Started time: {started_time}")
        logger.info(f"Elapsed working time: {elapsed_hours:.2f}")
        logger.info(
            f"Estimated finish time: {finish_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        logger.error("Could not calculate working hours.")
