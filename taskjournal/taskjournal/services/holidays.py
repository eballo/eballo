from collections import defaultdict
from datetime import date as datetime
from re import compile

from taskjournal.services.logger import logger


class HolidayService:
    def __init__(
        self,
        filepath: str,
        debug: bool = False,
    ) -> None:
        self.debug = debug
        self.holidays = {}  # Maps date object -> {description, category}
        self.categories = defaultdict(list)  # Maps category -> list of dates
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

    def is_holiday(self, date_obj: datetime) -> bool:
        """Returns the holiday info if the date is a holiday, else None."""
        return self.holidays.get(date_obj)

    def get_upcoming_holidays(self, limit=25) -> list[tuple[datetime, dict]]:
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

    def summary_upcoming(self, limit=25) -> None:
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
