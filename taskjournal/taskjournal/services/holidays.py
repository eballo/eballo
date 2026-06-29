from collections import defaultdict
from os import makedirs
from os.path import exists, join
from datetime import date as datetime
from re import compile

from taskjournal.config import BASE_DIR
from taskjournal.services.base import BaseService
from taskjournal.services.file import FileService
from taskjournal.services.logger import logger


class HolidayService(BaseService):
    def __init__(
        self,
        filepath: str,
        debug: bool = False,
    ) -> None:
        self.debug = debug
        self.holidays: dict[datetime, dict[str, str]] = (
            {}
        )  # Maps date object -> {description, category}
        self.categories: dict[str, list[datetime]] = defaultdict(
            list
        )  # Maps category -> list of dates
        self.load_and_parse(filepath)

    def load_and_parse(self, filepath: str) -> None:
        """Reads the file and parses dates, descriptions, and categories."""
        current_category = "Uncategorized"

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            logger.error(f"File '{filepath}' not found.")
            return

        # Regex pattern for YYYY-MM-DD
        date_pattern = compile(r"^(\d{4}-\d{2}-\d{2})\s+-\s+(.+)$")

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check for Section Headers (Categories)
            if line.startswith("#"):
                # Remove the # and whitespace to get clean category name
                current_category = line.lstrip("#").strip()
                continue

            # Check for Date Entries
            match = date_pattern.match(line)
            if match:
                date_str, description = match.groups()
                try:
                    date_obj = datetime.fromisoformat(date_str)

                    # Store the holiday data
                    holiday_info = {
                        "description": description,
                        "category": current_category,
                    }

                    self.holidays[date_obj] = holiday_info
                    self.categories[current_category].append(date_obj)

                except ValueError:
                    logger.warning(f"Invalid date format: {date_str}")

    def is_holiday(self, date_obj: datetime) -> dict[str, str] | None:
        """Returns the holiday info if the date is a holiday, else None."""
        return self.holidays.get(date_obj)

    def get_upcoming_holidays(
        self, limit: int = 50
    ) -> list[tuple[datetime, dict[str, str]]]:
        """Returns a list of the next X holidays from today."""
        today = datetime.today()
        upcoming = []

        # Sort dates to ensure order
        sorted_dates = sorted(self.holidays.keys())

        for date in sorted_dates:
            if date >= today:
                upcoming.append((date, self.holidays[date]))
                if len(upcoming) >= limit:
                    break
        return upcoming

    def get_past_holidays(self) -> list[tuple[datetime, dict[str, str]]]:
        """Returns a list of all holidays before today."""
        today = datetime.today()
        past = []

        # Sort dates to ensure order
        sorted_dates = sorted(self.holidays.keys())

        for date in sorted_dates:
            if date < today:
                past.append((date, self.holidays[date]))
        return past

    def summary_upcoming(self, limit: int = 50, sort_by: str = "date") -> None:
        """Prints a loaded summary of upcoming holidays."""
        upcoming_holidays = self.get_upcoming_holidays(limit)

        if sort_by == "category":
            upcoming_holidays.sort(key=lambda x: x[1]["category"])
        elif sort_by == "date":
            upcoming_holidays.sort(key=lambda x: x[0])
        else:
            raise ValueError("Invalid sort_by value. Use either 'category' or 'date'.")

        logger.info(f"--- Upcoming Holidays (next {len(upcoming_holidays)}) ---")
        # Find maximum description length for alignment
        max_desc_len = max(
            (len(info["description"]) for _, info in upcoming_holidays), default=0
        )

        today = datetime.today()
        for date, info in upcoming_holidays:
            desc = info["description"]
            category = info["category"]
            status = "[x]" if date < today else "[ ]"
            logger.info(f"{status} {date} : {desc:<{max_desc_len}} [{category}]")

    def summary_past(self, sort_by: str = "date") -> None:
        """Prints a loaded summary of past holidays."""
        past_holidays = self.get_past_holidays()

        if sort_by == "category":
            past_holidays.sort(key=lambda x: x[1]["category"])
        elif sort_by == "date":
            past_holidays.sort(key=lambda x: x[0])
        else:
            raise ValueError("Invalid sort_by value. Use either 'category' or 'date'.")

        logger.info(f"--- Past Holidays ({len(past_holidays)} total) ---")
        # Find maximum description length for alignment
        max_desc_len = max(
            (len(info["description"]) for _, info in past_holidays), default=0
        )

        today = datetime.today()
        for date, info in past_holidays:
            desc = info["description"]
            category = info["category"]
            status = "[x]" if date < today else "[ ]"
            logger.info(f"{status} {date} : {desc:<{max_desc_len}} [{category}]")

    def summary_all(self, sort_by: str = "date") -> None:
        """Prints a loaded summary by category."""

        if sort_by == "category":
            all_holidays = sorted(self.holidays.items(), key=lambda x: x[1]["category"])
        elif sort_by == "date":
            all_holidays = sorted(self.holidays.items())
        else:
            raise ValueError("Invalid sort_by value. Use either 'category' or 'date'.")

        logger.info(f"--- Holiday Summary ({len(all_holidays)} total) ---")
        # Find maximum description length for alignment
        max_desc_len = max(
            (len(info["description"]) for _, info in all_holidays), default=0
        )

        today = datetime.today()
        for date, info in all_holidays:
            desc = info["description"]
            category = info["category"]
            status = "[x]" if date < today else "[ ]"
            logger.info(f"{status} {date} : {desc:<{max_desc_len}} [{category}]")

    def populate_files(self) -> None:
        """Generates markdown files for all loaded holidays in the output directory."""

        count = 0
        for date_obj, info in self.holidays.items():
            week_folder = FileService.get_week_folder(BASE_DIR, date_obj)
            if not exists(week_folder):
                makedirs(week_folder, exist_ok=True)
                logger.info(f"Created directory: {week_folder}")
            # Format: 2025-01-06-DailyNotes-Holidays.md
            filename = f"{date_obj}-DailyNotes-Holidays.md"
            file_path = join(week_folder, filename)

            content = (
                f"Category: {info['category']}\n"
                f"Description: {info['description']}\n"
            )

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                count += 1
            except Exception as e:
                logger.error(f"Failed to write {filename}: {e}")

        logger.info(f"Successfully populated {count} holiday files")

    def get_days_until_next_holiday(self) -> tuple[int, datetime | None, str]:
        today = datetime.today()
        upcoming_holidays = self.get_upcoming_holidays(limit=1)

        if not upcoming_holidays:
            return 0, None, ""

        next_holiday_date, _ = upcoming_holidays[0]
        next_holiday_description = upcoming_holidays[0][1]["description"]
        days_until_holiday = (next_holiday_date - today).days
        return max(days_until_holiday, 0), next_holiday_date, next_holiday_description

    def add_holiday(self, filepath: str, date_str: str, description: str, category: str = "Personal days") -> None:
        try:
            date_obj = datetime.fromisoformat(date_str)
        except ValueError:
            logger.error(f"Invalid date format: {date_str}. Use YYYY-MM-DD.")
            return

        if date_obj in self.holidays:
            logger.warning(f"{date_str} is already registered: {self.holidays[date_obj]['description']}")
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            logger.error(f"File '{filepath}' not found. Run 'wk setup' first.")
            return

        new_line = f"{date_str} - {description}\n"
        target_header = f"## {category}"
        insert_at = None

        for i, line in enumerate(lines):
            if line.strip() == target_header:
                j = i + 1
                while j < len(lines) and (not lines[j].strip() or not lines[j].startswith("##")):
                    j += 1
                insert_at = j
                break

        if insert_at is None:
            lines.append(f"\n{target_header}\n")
            lines.append(new_line)
        else:
            lines.insert(insert_at, new_line)

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

        logger.info(f"Holiday added: {date_str} - {description} [{category}]")

    def summary(self) -> None:
        """Prints a general summary of holidays."""
        today = datetime.today()
        all_holidays = sorted(self.holidays.keys())
        total = len(all_holidays)

        if total == 0:
            logger.info("No holidays found.")
            return

        past = [d for d in all_holidays if d < today]
        upcoming = [d for d in all_holidays if d >= today]

        done = len(past)
        remaining = len(upcoming)
        percent = (done / total) * 100 if total > 0 else 0

        logger.info("--- Holiday Summary Statistics ---")
        logger.info(f"Total holidays: {total}")
        logger.info(f"Done:      {done} ({percent:.1f}%)")
        logger.info(f"Remaining:      {remaining}")

        if upcoming:
            days, next_date, next_desc = self.get_days_until_next_holiday()
            logger.info(f"Next holiday:   {next_desc} ({next_date}) - In {days} day(s)")
        else:
            logger.info("No more holidays left for this year!")
