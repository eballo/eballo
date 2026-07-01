from datetime import date, timedelta, datetime
from os.path import exists, join
from re import compile

from taskjournal.config import BASE_DIR, FIREMAN_WEEKS_FILE
from taskjournal.services.base import BaseService
from taskjournal.services.logger import console, logger


class FiremanService(BaseService):
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
            fireman_path = join(str(BASE_DIR), f"{year}/{FIREMAN_WEEKS_FILE}")
            logger.debug(f"Loading fireman weeks from {fireman_path}")
            with open(fireman_path, "r", encoding="utf-8") as f:
                date_pattern = compile(r"^(\d{4}-\d{2}-\d{2})")

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
            logger.warning(f"Fireman weeks file not found: {fireman_path}. Run 'wk setup' to create it.")

    def add_week(self, date_str: str) -> None:
        try:
            raw_date = date.fromisoformat(date_str)
        except ValueError:
            logger.error(f"Invalid date format: {date_str}. Use YYYY-MM-DD.")
            return

        monday = self._get_monday(raw_date)
        if monday in self.fireman_weeks:
            logger.warning(f"Week of {monday} is already registered as fireman.")
            return

        year = raw_date.year
        fireman_path = join(str(BASE_DIR), f"{year}/{FIREMAN_WEEKS_FILE}")
        try:
            with open(fireman_path, "a", encoding="utf-8") as f:
                f.write(f"{date_str}\n")
            self.fireman_weeks.add(monday)
            console.print(f"[green]✓[/green] Fireman week added: {date_str} (week of {monday})")
        except FileNotFoundError:
            logger.error(f"Fireman file not found: {fireman_path}. Run 'wk setup' first.")

    def get_all_weeks(self) -> list[date]:
        return sorted(self.fireman_weeks)

    def get_upcoming_weeks(self, today: date) -> list[date]:
        current_monday = self._get_monday(today)
        return [w for w in self.get_all_weeks() if w >= current_monday]

    def get_past_weeks(self, today: date) -> list[date]:
        current_monday = self._get_monday(today)
        return [w for w in self.get_all_weeks() if w < current_monday]

    def get_next_week(self, today: date) -> tuple[int, date | None]:
        upcoming = self.get_upcoming_weeks(today)
        if not upcoming:
            return 0, None
        next_monday = upcoming[0]
        days = (next_monday - today).days
        return max(days, 0), next_monday

    def summary(self, today: date) -> None:
        all_weeks = self.get_all_weeks()
        total = len(all_weeks)

        if total == 0:
            console.print("No fireman weeks registered.")
            return

        past = self.get_past_weeks(today)
        upcoming = self.get_upcoming_weeks(today)
        done = len(past)
        remaining = len(upcoming)
        percent = (done / total) * 100 if total > 0 else 0

        console.print(f"Total fireman weeks: {total}")
        console.print(f"Done:      {done} ({percent:.1f}%)")
        console.print(f"Remaining: {remaining}")

        days, next_monday = self.get_next_week(today)
        if next_monday:
            console.print(f"Next:      week of {next_monday} — in {days} day(s)")
        else:
            console.print("No upcoming fireman weeks.")

    def is_fireman_week(self) -> bool:
        """Returns True if the date's week is in the fireman list"""
        normalized_input = self._get_monday(self.create_datetime.date())
        is_fireman_week = normalized_input in self.fireman_weeks
        logger.debug(
            f"Checking if {self.create_datetime.date()} is a fireman week: {is_fireman_week}"
        )
        return is_fireman_week
