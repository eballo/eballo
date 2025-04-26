import os
import uuid
from datetime import datetime

from taskjournal.models.task import Task, Status
from taskjournal.parser.file_parser import ParseFile
from taskjournal.services.file import get_lines
from taskjournal.services.logger import logger


def get_tasks_from_daily_notes(file_path: str) -> list[Task]:
    try:
        lines = get_lines(file_path)
        tasks = ParseFile.get_tasks(lines)
        return tasks
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return []


def create_task(description: str) -> Task:
    return Task(
        id=str(uuid.uuid4()), description=description, status=Status.NOT_FINISHED
    )


def get_default_tasks() -> list[Task]:
    """Return the default tasks based on the day of the week."""
    base_tasks = ["Check emails", "Check Calendar", "PR reviews"]

    tasks = [create_task(desc) for desc in base_tasks]

    day_of_week = datetime.now().strftime("%A")
    week_number = datetime.now().isocalendar()[1]

    if day_of_week == "Wednesday":
        tasks.append(create_task("Check refinement tasks"))
    elif day_of_week == "Thursday" and week_number % 2 == 0:
        tasks.append(create_task("Get ready for the retro points"))
    elif day_of_week == "Friday":
        tasks.append(create_task("Write down the summary of the week"))

    return tasks


def get_previous_pending_tasks(folder_path: str, current_file: str) -> list[Task]:
    """Retrieve unfinished tasks from the most recent daily notes file."""
    if not os.path.exists(folder_path):
        return []
    daily_files = [
        f
        for f in os.listdir(folder_path)
        if f.endswith("DailyNotes.txt") and f != current_file
    ]
    if not daily_files:
        return []
    latest_file = os.path.join(folder_path, sorted(daily_files, reverse=True)[0])
    try:
        lines = get_lines(latest_file)
        pending_tasks = get_pending_tasks(lines)
        return pending_tasks
    except Exception as e:
        logger.warning(f"Warning: Could not read previous file {latest_file}: {e}")
        return []


def get_pending_tasks(lines: list[str]) -> list[Task]:
    tasks = ParseFile.get_tasks(lines)
    return [task for task in tasks if task.status == Status.NOT_FINISHED]
