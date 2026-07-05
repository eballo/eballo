from datetime import datetime
from json import load, dump, JSONDecodeError
from os import makedirs
from os.path import exists, join, dirname

from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus
from taskjournal.services.logger import logger


class FeedbackService(BaseService):
    """Stores and queries professional feedback entries (received and given)."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = base_dir

    @property
    def name(self) -> str:
        return "FeedbackService"

    def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(status=ServiceStatus.OK, message="Feedback service available")

    def _file_path(self, year: int) -> str:
        return join(self._base_dir, str(year), "feedback", "feedback.json")

    def _load(self, year: int) -> list[dict[str, object]]:
        path = self._file_path(year)
        if not exists(path):
            return []
        try:
            with open(path) as f:
                data = load(f)
            return data if isinstance(data, list) else []
        except (JSONDecodeError, OSError) as e:
            logger.warning(f"Could not read feedback file: {e}")
            return []

    def _save(self, year: int, entries: list[dict[str, object]]) -> None:
        path = self._file_path(year)
        makedirs(dirname(path), exist_ok=True)
        with open(path, "w") as f:
            dump(entries, f, indent=2)

    def add_received(
        self,
        text: str,
        from_person: str,
        context: str,
        date: datetime,
    ) -> None:
        entries = self._load(date.year)
        entries.append({
            "type": "received",
            "date": date.strftime("%Y-%m-%d"),
            "text": text,
            "from_person": from_person,
            "context": context,
        })
        self._save(date.year, entries)

    def add_given(
        self,
        text: str,
        to_person: str,
        context: str,
        date: datetime,
    ) -> None:
        entries = self._load(date.year)
        entries.append({
            "type": "given",
            "date": date.strftime("%Y-%m-%d"),
            "text": text,
            "to_person": to_person,
            "context": context,
        })
        self._save(date.year, entries)

    def list_feedback(
        self,
        year: int,
        quarter: int | None = None,
        person: str | None = None,
        feedback_type: str | None = None,
    ) -> list[dict[str, object]]:
        entries = self._load(year)
        result: list[dict[str, object]] = []
        for entry in entries:
            if feedback_type and entry.get("type") != feedback_type:
                continue
            if quarter:
                month = int(str(entry.get("date", "1970-01")).split("-")[1])
                entry_quarter = (month - 1) // 3 + 1
                if entry_quarter != quarter:
                    continue
            if person:
                person_lower = person.lower()
                from_match = str(entry.get("from_person", "")).lower() == person_lower
                to_match = str(entry.get("to_person", "")).lower() == person_lower
                if not (from_match or to_match):
                    continue
            result.append(entry)
        return result

    def get_for_period(self, start: datetime, end: datetime) -> list[dict[str, object]]:
        years = range(start.year, end.year + 1)
        all_entries: list[dict[str, object]] = []
        for year in years:
            for entry in self._load(year):
                try:
                    entry_date = datetime.strptime(str(entry.get("date", "")), "%Y-%m-%d")
                    if start <= entry_date <= end:
                        all_entries.append(entry)
                except ValueError:
                    continue
        return all_entries
