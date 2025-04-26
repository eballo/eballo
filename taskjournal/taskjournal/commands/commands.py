import os
from datetime import datetime

from taskjournal.config import DAILY_NOTES_END_TEMPLATE
from taskjournal.models.task import Status
from taskjournal.repositories.file_writer import FileWriter
from taskjournal.services.file import (
    load_template,
    check_finalized_in_file,
    write_to_file,
    write_lines_to_file,
    get_lines,
)
from taskjournal.services.logger import logger
from taskjournal.services.task_manager import (
    get_default_tasks,
    get_tasks_from_daily_notes,
    get_previous_pending_tasks,
)
from taskjournal.services.time import (
    get_total_time_from_daily_notes,
    estimated_finish_time,
    get_start_time,
    calculate_working_hours,
)


def create_daily_notes_file(file_path: str, template_path: str) -> datetime:
    """
    Create a daily file using a template and adding a creation timestamp.

    Args:
        file_path (str): The path for the new daily notes file.
        template_path (str): The path to the template file.
    """

    # Load template and add timestamp
    template_content = load_template(template_path)

    create_datetime = datetime.now()
    creation_time_str = create_datetime.strftime("%Y-%m-%d %H:%M:%S")
    daily_notes_content = template_content.replace(
        "{{creation_time}}", creation_time_str
    )

    # Get tasks: unfinished tasks + default tasks
    default_tasks = get_default_tasks()
    folder_path = os.path.dirname(file_path)
    previous_pending_tasks = get_previous_pending_tasks(
        folder_path, os.path.basename(file_path)
    )

    tasks = default_tasks + previous_pending_tasks
    FileWriter.save_tasks(file_path, daily_notes_content, tasks)

    return estimated_finish_time(create_datetime)


def finalize_daily_notes(file_path: str, custom_date: datetime | None) -> None:
    """Add a final timestamp to the daily notes file and calculate total time spent."""

    if check_finalized_in_file(file_path) and not custom_date:
        logger.info(f"File '{file_path}' is already finalized.")
        return

    content = get_lines(file_path)
    created_line_index, created_time = get_start_time(content)

    if not custom_date:
        final_time = datetime.now()
    else:
        logger.info(f"Custom date provided: {custom_date}")
        final_time = custom_date

    # Calculate finalized time and total time spent
    total_time_spent = final_time - created_time
    finalized_line = f"Finalized: {final_time.strftime('%Y-%m-%d %H:%M')}\n"
    total_time_line = f"Total Time Spent: {total_time_spent}\n"

    # Remove old Finalized and Total Time Spent lines if they exist
    content = [
        line
        for line in content
        if not line.startswith("Finalized:")
        and not line.startswith("Total Time Spent:")
    ]

    # Insert finalized time and total time spent below the creation date
    content.insert(created_line_index + 1, finalized_line)
    content.insert(created_line_index + 2, total_time_line)
    write_lines_to_file(file_path, content)

    template_content = load_template(DAILY_NOTES_END_TEMPLATE)
    normalized_template_content = template_content.replace("\n", "")
    normalized_content = "".join(content).replace("\n", " ")

    if normalized_template_content not in normalized_content:
        write_to_file(file_path, template_content, "a")

    logger.info(f"Daily notes finalized with timestamp: {file_path}")


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
            daily_pending = [
                task for task in tasks if task.status == Status.NOT_FINISHED
            ]
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
    total_minutes, total_seconds = divmod(remainder, 60)

    week_summary_content = week_summary_content.replace(
        "{{total_time}}", f" {total_hours} hours and {total_minutes} minutes"
    )
    week_summary_content = week_summary_content.replace(
        "{{done_tasks}}", "\n".join(f"[x] {task}" for task in done_tasks)
    )
    week_summary_content = week_summary_content.replace(
        "{{pending_tasks}}", "\n".join(f"[ ] {task}" for task in pending_tasks)
    )
    week_summary_content = week_summary_content.replace(
        "{{summary}}", "\nWrite your weekly summary here...\n"
    )

    write_to_file(summary_file, week_summary_content)


def create_retro_file(week_folder: str, template_path: str) -> str:
    """Create a retro file using a template."""
    retro_file = os.path.join(week_folder, "retro.txt")

    if not os.path.exists(retro_file):
        template_content = load_template(template_path)
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
