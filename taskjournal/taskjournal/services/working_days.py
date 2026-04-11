import os
from datetime import date as datetime  # Keeping your alias convention
from datetime import timedelta
from typing import Any

from taskjournal.config import BASE_DIR, HOLIDAYS_FILE
from taskjournal.constants import WORK_LOCATION_HOME, WORK_LOCATION_OFFICE
from taskjournal.services.holidays import HolidayService
from taskjournal.services.logger import logger
from taskjournal.services.parser import DailyParserService
from taskjournal.services.time import (
    get_daily_notes_name,
    get_total_time_from_daily_notes,
)


class WorkingDaysService:
    def __init__(self, year: str | int, debug: bool = False) -> None:
        self.year = year
        holidays_path = os.path.join(BASE_DIR, f"{year}/{HOLIDAYS_FILE}")
        self.holiday_service = HolidayService(filepath=holidays_path)
        self.debug = debug

    def _analyze_year(self, year: str | int) -> list[dict[str, Any]]:
        """
        Internal helper: Generates a day-by-day classification for the entire year.
        Returns a list of dicts: {'date': date_obj, 'type': 'weekend'|'holiday'|'workday'}
        """
        start_date = datetime(int(year), 1, 1)
        end_date = datetime(int(year), 12, 31)

        # Calculate total days in year
        total_days = (end_date - start_date).days + 1

        analysis = []

        for i in range(total_days):
            current_day = start_date + timedelta(days=i)
            day_type = "workday"

            # 1. Check Weekend (Saturday=5, Sunday=6)
            if current_day.weekday() >= 5:
                day_type = "weekend"

            # 2. Check Holiday (Only if it's not already a weekend to avoid double counting)
            elif self.holiday_service and self.holiday_service.is_holiday(current_day):
                day_type = "holiday"

            analysis.append({"date": current_day, "type": day_type})

        return analysis

    def summary(self) -> dict[str, Any]:
        """
        Returns an overview of the theoretical capacity of the year.
        """
        data = self._analyze_year(self.year)

        total_days = len(data)
        weekends = sum(1 for d in data if d["type"] == "weekend")
        holidays = sum(1 for d in data if d["type"] == "holiday")
        workdays = sum(1 for d in data if d["type"] == "workday")

        summary_data = {
            "year": self.year,
            "total_calendar_days": total_days,
            "total_weekends": weekends,
            "holidays_on_weekdays": holidays,
            "theoretical_working_days": workdays + holidays,  # Mon-Fri count
            "real_working_days": workdays,  # Mon-Fri minus Holidays
        }

        logger.info(f"--- Summary for {self.year} ---")
        logger.info(f"Total Days: {total_days}")
        logger.info(f"Real Working Days: {workdays}")

        return summary_data

    def get_progress(self) -> dict[str, Any]:
        """
        Calculates days already worked vs days missing based on today's date.
        Tracks holidays, weekends (taken/total), and percentage completion.
        """
        today = datetime.today()
        data = self._analyze_year(self.year)

        worked_count = 0
        missing_count = 0
        holidays_taken = 0
        holidays_remaining = 0
        total_weekends = 0
        weekends_taken = 0

        # Calendar counters
        days_elapsed = 0
        total_calendar_days = len(data)

        for entry in data:
            entry_date = entry["date"]
            entry_type = entry["type"]

            # Count calendar days elapsed (includes today)
            if entry_date <= today:
                days_elapsed += 1

            # Workday logic
            if entry_type == "workday":
                if entry_date <= today:
                    worked_count += 1
                else:  # entry_date >= today
                    missing_count += 1

            # Holiday logic
            elif entry_type == "holiday":
                if entry_date <= today:
                    holidays_taken += 1
                else:  # entry_date >= today
                    holidays_remaining += 1

            # Weekend logic
            elif entry_type == "weekend":
                total_weekends += 1
                if entry_date <= today:
                    weekends_taken += 1

        weekends_remaining = total_weekends - weekends_taken
        total_workdays = worked_count + missing_count

        # Calculate percentage
        if total_workdays > 0:
            progress_percent = (worked_count / total_workdays) * 100
        else:
            progress_percent = 0.0

        logger.info(f"--- Progress for {self.year} ---")
        logger.info(f"Work Progress: {progress_percent:.2f}%")
        logger.info(f"Day: {days_elapsed} / {total_calendar_days}")
        logger.info(f"Days Worked: {worked_count} / {missing_count}")
        logger.info(f"Holidays: {holidays_taken} / {holidays_remaining}")
        logger.info(f"Weekends: {weekends_taken} / {total_weekends}")

        return {
            "current_day_number": days_elapsed,
            "total_calendar_days": total_calendar_days,
            "worked": worked_count,
            "missing": missing_count,
            "holidays_taken": holidays_taken,
            "holidays_remaining": holidays_remaining,
            "total_weekends": total_weekends,
            "weekends_taken": weekends_taken,
            "weekends_remaining": weekends_remaining,
            "total_workdays": total_workdays,
            "total_holidays": holidays_taken + holidays_remaining,
            "progress_percentage": round(progress_percent, 2),
        }

    def get_real_working_days(self) -> int:
        """
        Returns the exact number of working days taking holidays into account.
        """
        data = self._analyze_year(self.year)
        real_days = sum(1 for d in data if d["type"] == "workday")

        logger.info(f"Real working days in {self.year}: {real_days}")
        return real_days

    def get_week_stats(self, custom_date: datetime, week_folder: str) -> dict[str, Any]:
        """
        Calculates weekly statistics based on daily notes in the week folder.
        """
        total_time_seconds = 0
        days_at_office = 0
        days_at_home = 0
        total_worked_days = 0
        vacation_days = 0

        parser = DailyParserService()

        # Get start of week (Monday) and end of week (Friday)
        start_of_week = custom_date - timedelta(days=custom_date.weekday())
        end_of_week = start_of_week + timedelta(days=4)

        for i in range(5):  # Monday to Friday
            day = start_of_week + timedelta(days=i)
            daily_notes_name = get_daily_notes_name(day)
            daily_file_path = os.path.join(week_folder, daily_notes_name)

            if os.path.exists(daily_file_path):
                total_worked_days += 1
                daily_time = get_total_time_from_daily_notes(daily_file_path)
                total_time_seconds += daily_time

                # Extract statistics
                data = parser.parse(daily_file_path)
                if data:
                    work_from = data.get("work_from", "").strip().capitalize()
                    if WORK_LOCATION_OFFICE.lower() in work_from.lower():
                        days_at_office += 1
                    elif WORK_LOCATION_HOME.lower() in work_from.lower():
                        days_at_home += 1
            else:
                # If no daily note, it's a vacation day or a holiday
                vacation_days += 1

        return {
            "start_date": start_of_week,
            "end_date": end_of_week,
            "total_time_seconds": total_time_seconds,
            "total_worked_days": total_worked_days,
            "vacation_days": vacation_days,
            "days_at_office": days_at_office,
            "days_at_home": days_at_home,
        }
