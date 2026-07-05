from datetime import datetime
from os import listdir
from os.path import exists, join
from uuid import uuid4

from taskjournal.config import TEMPLATE_FORMAT
from taskjournal.constants import (
    WORK_OFFICE_DAYS,
    WORK_LOCATION_HOME,
    WORK_LOCATION_OFFICE,
)
from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Task, Status, Epic
from taskjournal.services.base import BaseService
from taskjournal.services.logger import logger
from taskjournal.services.parser import DailyParserService
from taskjournal.services.wifi import WifiService


class TaskManager(BaseService):

    def __init__(
        self,
        parser: DailyParserService,
        wifi_service: WifiService,
    ) -> None:
        self.parser = parser
        self.wifi_service = wifi_service

    def get_tasks_from_daily_notes(self, file_path: str) -> list[Task]:
        try:
            note = self.parser.parse(file_path)
            if note is None:
                logger.error(f"Error reading file {file_path}")
                return []
            return note.planned_tasks
        except Exception:
            logger.error(f"Error reading file {file_path}")
            return []

    @staticmethod
    def create_task(description: str) -> Task:
        return Task(
            id=str(uuid4()), key=None, description=description, status=Status.TODO
        )

    def get_work_from_location(self, date: datetime) -> str:
        wifi_location = self._get_location_from_wifi()
        default_location = TaskManager._get_default_locations(date)
        work_from = wifi_location if wifi_location else default_location
        logger.debug(f"Work from: {work_from}")
        return work_from

    @staticmethod
    def _get_default_locations(date: datetime) -> str:
        day_of_week = date.strftime("%A")
        if day_of_week in WORK_OFFICE_DAYS:
            working_from_location = WORK_LOCATION_OFFICE
        else:
            working_from_location = WORK_LOCATION_HOME
        logger.debug(f"Day of the week: {day_of_week} - Location: {working_from_location}")
        return working_from_location

    def get_wifi_location(self) -> str | None:
        wifi_name = self.wifi_service.get_name()
        logger.debug(f"WiFi name: {wifi_name}")
        if wifi_name == self.wifi_service.home_wifi:
            return WORK_LOCATION_HOME
        if wifi_name == self.wifi_service.office_wifi:
            return WORK_LOCATION_OFFICE
        return None

    def _get_location_from_wifi(self) -> str | None:
        return self.get_wifi_location()

    @staticmethod
    def get_default_tasks() -> list[Task]:
        return []

    def get_previous_pending_tasks(
        self,
        folder_path: str,
        current_file: str,
    ) -> list[Task]:
        """Retrieve unfinished tasks from the most recent daily notes file."""
        if not exists(folder_path):
            return []
        daily_files = [
            f
            for f in listdir(folder_path)
            if f.endswith(f"DailyNotes.{TEMPLATE_FORMAT}") and f != current_file
        ]
        if not daily_files:
            return []
        latest_file = join(folder_path, sorted(daily_files, reverse=True)[0])
        try:
            data = self.parser.parse(latest_file)
            if data is None:
                return []
            return TaskManager.get_pending_tasks(data)
        except Exception as e:
            logger.warning(f"Warning: Could not read previous file {latest_file}: {e}")
            return []

    @staticmethod
    def get_pending_tasks(note: ParsedNote) -> list[Task]:
        return [task for task in note.planned_tasks if task.status == Status.TODO]

    @staticmethod
    def unique_tasks(tasks: list[Task]) -> list[Task]:
        seen_keys: set[str] = set()
        seen_descs: set[str] = set()
        result: list[Task] = []
        for task in tasks:
            if task.key and task.key in seen_keys:
                continue
            normalized = task.description.strip().lower()
            if normalized in seen_descs:
                # Replace a keyless placeholder with the keyed Jira version.
                if task.key:
                    result = [t for t in result if t.description.strip().lower() != normalized]
                    seen_keys.add(task.key)
                    result.append(task)
                continue
            if task.key:
                seen_keys.add(task.key)
            seen_descs.add(normalized)
            result.append(task)
        return result

    @staticmethod
    def get_unique_epics(tasks: list[Task]) -> list[Epic]:
        seen: dict[str, Epic] = {}
        for task in tasks:
            if task.epic and task.epic.key not in seen:
                seen[task.epic.key] = task.epic
        return list(seen.values())

    @staticmethod
    def get_unique_epic_names(tasks: list[Task]) -> list[str]:
        seen: dict[str, str] = {}
        for task in tasks:
            if task.epic and task.epic.key not in seen:
                seen[task.epic.key] = task.epic.summary
        return list(seen.values())
