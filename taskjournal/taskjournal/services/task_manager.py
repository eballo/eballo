import os
import uuid
from datetime import datetime
from typing import List, Dict

from taskjournal.config import TEMPLATE_FORMAT
from taskjournal.constants import BASE_TASKS, EXTENDED_TASKS, WORK_OFFICE_DAYS
from taskjournal.models.task import Task, Status, Epic
from taskjournal.services.logger import logger
from taskjournal.services.parser import DailyParserService


def get_tasks_from_daily_notes(file_path: str) -> list[Task]:
    try:
        daily_parser = DailyParserService()
        data = daily_parser.parse(file_path)
        tasks = data.get("planned_tasks", [])
        return tasks
    except Exception as e:
        logger.error(f"Error reading file {file_path}")
        return []


def create_task(description: str) -> Task:
    return Task(
        id=str(uuid.uuid4()), key=None, description=description, status=Status.TODO
    )


def get_work_from_defaults(date: datetime) -> str:
    day_of_week = date.strftime("%A")
    if day_of_week in WORK_OFFICE_DAYS:
        return "Office"
    else:
        return "Home"


def get_default_tasks() -> list[Task]:
    """Return the default tasks based on the day of the week."""
    tasks: List[Task] = [create_task(desc) for desc in BASE_TASKS]

    now = datetime.now()
    day_of_week = now.strftime("%A")
    week_number = now.isocalendar()[1]

    if day_of_week == "Monday":
        tasks.append(create_task(EXTENDED_TASKS[3]))
    elif day_of_week == "Wednesday":
        tasks.append(create_task(EXTENDED_TASKS[0]))
    elif day_of_week == "Thursday" and week_number % 2 == 0:
        tasks.append(create_task(EXTENDED_TASKS[1]))
    elif day_of_week == "Friday":
        tasks.append(create_task(EXTENDED_TASKS[2]))

    return tasks


def get_previous_pending_tasks(folder_path: str, current_file: str) -> list[Task]:
    """Retrieve unfinished tasks from the most recent daily notes file."""
    if not os.path.exists(folder_path):
        return []
    daily_files = [
        f
        for f in os.listdir(folder_path)
        if f.endswith(f"DailyNotes.{TEMPLATE_FORMAT}") and f != current_file
    ]
    if not daily_files:
        return []
    latest_file = os.path.join(folder_path, sorted(daily_files, reverse=True)[0])
    try:
        daily_parser = DailyParserService()
        data = daily_parser.parse(latest_file)
        return get_pending_tasks(data)
    except Exception as e:
        logger.warning(f"Warning: Could not read previous file {latest_file}: {e}")
        return []


def get_pending_tasks(data: dict) -> list[Task]:
    tasks = data.get("planned_tasks", [])
    return [task for task in tasks if task.status == Status.TODO]


def unique_tasks(tasks: list[Task]) -> list[Task]:
    seen = set()
    unique_tasks = []
    for task in tasks:
        if task.description not in seen:
            seen.add(task.description)
            unique_tasks.append(task)
    return unique_tasks


def get_unique_epics(tasks: List[Task]) -> List[Epic]:
    seen: Dict[str, Epic] = {}
    for task in tasks:
        if task.epic and task.epic.key not in seen:
            seen[task.epic.key] = task.epic
    return list(seen.values())
