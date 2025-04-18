import os
from datetime import datetime

from taskjournal.config import DAILY_NOTES_END_TEMPLATE
from taskjournal.services.file import (
    load_template,
    check_finalized_in_file,
    write_to_file,
    write_lines_to_file,
)
from taskjournal.services.logger import logger
from taskjournal.services.task_manager import (
    get_default_tasks,
    get_tasks_from_daily_notes,
    get_previous_tasks,
)
from taskjournal.services.time import (
    get_total_time_from_daily_notes,
    estimated_finish_time,
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
    folder_path = os.path.dirname(file_path)
    previous_tasks = get_previous_tasks(folder_path, os.path.basename(file_path))
    default_tasks = get_default_tasks()
    unique_tasks = list(dict.fromkeys(default_tasks + previous_tasks))
    daily_notes_content = daily_notes_content.replace(
        "{{tasks}}", "\n".join(unique_tasks)
    )

    # Write the daily notes file
    write_to_file(file_path, daily_notes_content)

    return estimated_finish_time(create_datetime)


def finalize_daily_notes(file_path: str) -> None:
    """Add a final timestamp to the daily notes file and calculate total time spent."""

    if check_finalized_in_file(file_path):
        logger.info(f"File '{file_path}' is already finalized.")
        return

    with open(file_path, "r") as file:
        lines = file.readlines()

    # Find the creation date line
    for i, line in enumerate(lines):
        if line.startswith("Start time:"):
            created_line_index = i
            created_time = datetime.strptime(
                line.split("Start time:")[1].strip(), "%Y-%m-%d %H:%M:%S"
            )
            break
    else:
        raise ValueError("Creation date not found in the file.")

    # Calculate finalized time and total time spent
    final_time = datetime.now()
    total_time_spent = final_time - created_time
    finalized_line = f"Finalized: {final_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    total_time_line = f"Total Time Spent: {total_time_spent}\n"

    # Insert finalized time and total time spent below the creation date
    lines.insert(created_line_index + 1, finalized_line)
    lines.insert(created_line_index + 2, total_time_line)

    # Write back the updated file
    write_lines_to_file(file_path, lines)

    template_content = load_template(DAILY_NOTES_END_TEMPLATE)
    write_to_file(template_content, file_path, "a")
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
            daily_done, daily_pending = get_tasks_from_daily_notes(daily_file_path)
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
