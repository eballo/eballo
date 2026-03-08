import os
import re
from datetime import date, timedelta, datetime

from taskjournal.config import BASE_DIR, FIREMAN_WEEKS_FILE
from taskjournal.services.logger import logger


class FiremanService:
    def __init__(self, create_datetime: datetime) -> None:
        self.fireman_weeks: set[date] = set()
        self.create_datetime = create_datetime
        self.load_and_parse()

    @staticmethod
    def _get_monday(date_obj: date) -> date:
        """Normalizes any date to the Monday of that week"""
        return date_obj - timedelta(days=date_obj.weekday())

    def load_and_parse(self) -> None:
        try:
            year = self.create_datetime.date().year
            fireman_path = os.path.join(BASE_DIR, f"{year}/{FIREMAN_WEEKS_FILE}")
            logger.debug(f"Loading fireman weeks from {fireman_path}")
            with open(fireman_path, "r", encoding="utf-8") as f:
                date_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})")

                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    match = date_pattern.match(line)
                    if match:
                        try:
                            raw_date = date.fromisoformat(match.group(1))
                            monday_date = self._get_monday(raw_date)
                            self.fireman_weeks.add(monday_date)
                        except ValueError:
                            logger.error(f"Invalid date: {line}")
        except FileNotFoundError:
            logger.error(f"Error: File '{fireman_path}' not found.")

    def is_fireman_week(self) -> bool:
        """Returns True if the date's week is in the fireman list"""
        normalized_input = self._get_monday(self.create_datetime.date())
        is_fireman_week = normalized_input in self.fireman_weeks
        logger.info(
            f"Checking if {self.create_datetime.date()} is a fireman week: {is_fireman_week}"
        )
        return is_fireman_week
