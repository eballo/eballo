import os
from collections import defaultdict
from datetime import date as datetime
from re import compile

from taskjournal.config import BASE_DIR
from taskjournal.services.file import get_week_folder
from taskjournal.services.logger import logger


class HolidayService:
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
            print(f"Error: File '{filepath}' not found.")
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
                    print(f"Warning: Invalid date format found: {date_str}")

    def is_holiday(self, date_obj: datetime) -> dict[str, str] | None:
        """Returns the holiday info if the date is a holiday, else None."""
        return self.holidays.get(date_obj)

    def get_upcoming_holidays(
        self, limit: int = 25
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

    def summary_upcoming(self, limit: int = 25) -> None:
        """Prints a loaded summary of upcoming holidays."""
        upcoming_holidays = self.get_upcoming_holidays(limit)
        logger.info(f"--- Upcoming Holidays (next {len(upcoming_holidays)}) ---")
        for date, info in upcoming_holidays:
            desc = info["description"]
            category = info["category"]
            logger.info(f"  {date} [{category}]: {desc}")

    def summary_all(self) -> None:
        """Prints a loaded summary by category."""
        logger.info(f"--- Holiday Summary ({len(self.holidays)} total) ---")
        for category, dates in self.categories.items():
            logger.info(f"\n[{category}]")
            for date in dates:
                desc = self.holidays[date]["description"]
                logger.info(f"  {date}: {desc}")

    def populate_files(self) -> None:
        """Generates markdown files for all loaded holidays in the output directory."""

        count = 0
        for date_obj, info in self.holidays.items():
            week_folder = get_week_folder(BASE_DIR, date_obj)
            if not os.path.exists(week_folder):
                os.makedirs(week_folder)
                logger.info(f"Created directory: {week_folder}")
            # Format: 2025-01-06-DailyNotes-Holidays.md
            filename = f"{date_obj}-DailyNotes-Holidays.md"
            file_path = os.path.join(week_folder, filename)

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
