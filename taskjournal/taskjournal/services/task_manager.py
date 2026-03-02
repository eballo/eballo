import os
import uuid
from datetime import datetime
from typing import List, Dict

from taskjournal.config import TEMPLATE_FORMAT, HOME_WIFI, OFFICE_WIFI
from taskjournal.constants import (
    BASE_TASKS,
    EXTENDED_TASKS,
    WORK_OFFICE_DAYS,
    WORK_LOCATION_HOME,
    WORK_LOCATION_OFFICE,
)
from taskjournal.models.task import Task, Status, Epic
from taskjournal.services.logger import logger
from taskjournal.services.parser import DailyParserService
from taskjournal.services.wifi import WifiService


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


def get_work_from_location(date: datetime) -> str:
    wifi_location = _get_location_from_wifi()
    default_location = _get_default_locations(date)
    work_from = wifi_location if wifi_location else default_location
    logger.info(f"Work from: {work_from}")
    return work_from


def _get_default_locations(date: datetime) -> str:
    day_of_week = date.strftime("%A")
    if day_of_week in WORK_OFFICE_DAYS:
        working_from_location = WORK_LOCATION_OFFICE
    else:
        working_from_location = WORK_LOCATION_HOME
    logger.debug(f"Day of the week: {day_of_week} - Location: {working_from_location}")
    return working_from_location


def _get_location_from_wifi() -> str | None:
    wifi_service = WifiService()
    wifi_name = wifi_service.get_name()
    working_from_location = None
    logger.debug(f"WiFi name: {wifi_name}")
    if wifi_name == HOME_WIFI:
        working_from_location = WORK_LOCATION_HOME
    elif wifi_name == OFFICE_WIFI:
        working_from_location = WORK_LOCATION_OFFICE
    return working_from_location


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
