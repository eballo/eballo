from __future__ import annotations

from datetime import datetime, timedelta
from json import load as json_load, dump as json_dump, JSONDecodeError
from os import makedirs
from os.path import exists, join, dirname

from taskjournal.config import BASE_DIR
from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus
from taskjournal.services.logger import logger

_RECURRING_FILE = join(str(BASE_DIR), "recurring", "recurring_tasks.json")

_ALL_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
_DOW_MAP = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

MONTHLY_FIRST_WORKDAY = "monthly_first_workday"


def _is_first_workday_of_month(day: datetime) -> bool:
    first = day.replace(day=1)
    while first.weekday() >= 5:
        first += timedelta(days=1)
    return day.date() == first.date()


class RecurringTasksService(BaseService):
    """Manages a JSON file of recurring tasks that auto-inject into daily notes."""

    def __init__(self, file_path: str = _RECURRING_FILE) -> None:
        self._file = file_path

    @property
    def name(self) -> str:
        return "RecurringTasksService"

    def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status=ServiceStatus.OK, message="Recurring tasks service available")

    def _load(self) -> list[dict[str, object]]:
        if not exists(self._file):
            return []
        try:
            with open(self._file) as f:
                data = json_load(f)
            return data if isinstance(data, list) else []
        except (JSONDecodeError, OSError) as exc:
            logger.warning(f"Could not read recurring tasks file: {exc}")
            return []

    def _save(self, tasks: list[dict[str, object]]) -> None:
        makedirs(dirname(self._file), exist_ok=True)
        with open(self._file, "w") as f:
            json_dump(tasks, f, indent=2)

    def add(
        self,
        description: str,
        days: list[str] | None = None,
        monthly: bool = False,
    ) -> None:
        tasks = self._load()
        normalised_days: list[str] | str

        if monthly:
            normalised_days = MONTHLY_FIRST_WORKDAY
        elif not days:
            normalised_days = "every"
        else:
            normalised_days = [d.lower() for d in days]
            for d in normalised_days:
                if d not in _ALL_DAYS:
                    raise ValueError(f"Unknown day: {d!r}. Use full weekday names.")

        for t in tasks:
            if t.get("description") == description:
                t["days"] = normalised_days
                self._save(tasks)
                logger.info(f"Updated recurring task: {description!r}")
                return

        tasks.append({"description": description, "days": normalised_days})
        self._save(tasks)
        logger.info(f"Added recurring task: {description!r}")

    def remove(self, description: str) -> bool:
        tasks = self._load()
        before = len(tasks)
        tasks = [t for t in tasks if t.get("description") != description]
        if len(tasks) == before:
            return False
        self._save(tasks)
        return True

    def list_all(self) -> list[dict[str, object]]:
        return self._load()

    def get_for_day(self, day: datetime) -> list[str]:
        dow = _DOW_MAP[day.weekday()]
        result: list[str] = []
        for t in self._load():
            task_days = t.get("days", "every")
            if task_days == "every":
                include = True
            elif task_days == MONTHLY_FIRST_WORKDAY:
                include = _is_first_workday_of_month(day)
            else:
                include = dow in task_days  # type: ignore[operator]
            if include:
                desc = t.get("description", "")
                if isinstance(desc, str) and desc:
                    result.append(desc)
        return result
