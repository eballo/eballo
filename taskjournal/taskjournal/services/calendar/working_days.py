from calendar import monthrange
from datetime import date as datetime
from os.path import exists, join
from datetime import timedelta
from typing import Any

from taskjournal.config import BASE_DIR, HOLIDAYS_FILE
from taskjournal.constants import WORK_LOCATION_HOME, WORK_LOCATION_OFFICE
from taskjournal.models.parsed_note import ParsedNote
from taskjournal.services.base import BaseService
from taskjournal.services.file import FileService
from taskjournal.services.calendar.holidays import HolidayService
from taskjournal.services.logger import logger
from taskjournal.services.parser import DailyParserService
from taskjournal.services.time import TimeService


class WorkingDaysService(BaseService):
    def __init__(
        self,
        year: str | int,
        holiday_service: HolidayService | None = None,
        parser: DailyParserService | None = None,
        debug: bool = False,
    ) -> None:
        self.year = year
        self.debug = debug
        if holiday_service is None:
            holidays_path = join(BASE_DIR, f"{year}/{HOLIDAYS_FILE}")
            holiday_service = HolidayService(filepath=holidays_path)
        self.holiday_service = holiday_service
        self.parser = parser or DailyParserService()

    # --- private helpers ---

    @staticmethod
    def _classify_work_location(note: ParsedNote) -> tuple[bool, bool]:
        work_from = note.work_from.strip().capitalize()
        is_office = WORK_LOCATION_HOME.lower() not in work_from.lower() and WORK_LOCATION_OFFICE.lower() in work_from.lower()
        is_home = WORK_LOCATION_HOME.lower() in work_from.lower()
        return is_office, is_home

    def _process_daily_file(self, daily_file_path: str) -> dict[str, Any]:
        time_seconds = TimeService.get_total_time_from_daily_notes(daily_file_path)
        is_office = is_home = False
        summary_lines: list[str] = []

        note = self.parser.parse(daily_file_path)
        if note:
            is_office, is_home = self._classify_work_location(note)
            raw_summary = note.summary
            if raw_summary:
                text = " ".join(line for line in raw_summary if line.strip())
                if text:
                    summary_lines.append(text)

        return {
            "time_seconds": time_seconds,
            "is_office": is_office,
            "is_home": is_home,
            "summary_lines": summary_lines,
        }

    def _analyze_year(self, year: str | int) -> list[dict[str, Any]]:
        start_date = datetime(int(year), 1, 1)
        end_date = datetime(int(year), 12, 31)
        total_days = (end_date - start_date).days + 1

        analysis = []
        for i in range(total_days):
            current_day = start_date + timedelta(days=i)
            day_type = "workday"

            if current_day.weekday() >= 5:
                day_type = "weekend"
            elif self.holiday_service and self.holiday_service.is_holiday(current_day):
                day_type = "holiday"

            analysis.append({"date": current_day, "type": day_type})

        return analysis

    # --- public methods ---

    def summary(self) -> dict[str, Any]:
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
            "theoretical_working_days": workdays + holidays,
            "real_working_days": workdays,
        }

        logger.info(f"--- Summary for {self.year} ---")
        logger.info(f"Total Days: {total_days}")
        logger.info(f"Real Working Days: {workdays}")

        return summary_data

    def get_progress(self) -> dict[str, Any]:
        today = datetime.today()
        data = self._analyze_year(self.year)

        worked_count = missing_count = 0
        holidays_taken = holidays_remaining = 0
        total_weekends = weekends_taken = 0
        days_elapsed = 0
        total_calendar_days = len(data)

        for entry in data:
            entry_date = entry["date"]
            entry_type = entry["type"]

            if entry_date <= today:
                days_elapsed += 1

            if entry_type == "workday":
                if entry_date <= today:
                    worked_count += 1
                else:
                    missing_count += 1
            elif entry_type == "holiday":
                if entry_date <= today:
                    holidays_taken += 1
                else:
                    holidays_remaining += 1
            elif entry_type == "weekend":
                total_weekends += 1
                if entry_date <= today:
                    weekends_taken += 1

        weekends_remaining = total_weekends - weekends_taken
        total_workdays = worked_count + missing_count
        progress_percent = (worked_count / total_workdays * 100) if total_workdays > 0 else 0.0

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
        data = self._analyze_year(self.year)
        real_days = sum(1 for d in data if d["type"] == "workday")
        logger.info(f"Real working days in {self.year}: {real_days}")
        return real_days

    def get_week_stats(self, custom_date: datetime, week_folder: str) -> dict[str, Any]:
        total_time_seconds = days_at_office = days_at_home = 0
        total_worked_days = vacation_days = 0

        start_of_week = custom_date - timedelta(days=custom_date.weekday())
        end_of_week = start_of_week + timedelta(days=4)

        for i in range(5):  # Monday to Friday
            day = start_of_week + timedelta(days=i)
            daily_notes_name = TimeService.get_daily_notes_name(day)
            daily_file_path = join(week_folder, daily_notes_name)

            if exists(daily_file_path):
                total_worked_days += 1
                stats = self._process_daily_file(daily_file_path)
                total_time_seconds += stats["time_seconds"]
                if stats["is_office"]:
                    days_at_office += 1
                elif stats["is_home"]:
                    days_at_home += 1
            else:
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

    def get_month_stats(self, custom_date: datetime, base_dir: str) -> dict[str, Any]:
        year = custom_date.year
        month = custom_date.month

        _, last_day = monthrange(year, month)
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, last_day)

        total_time_seconds = days_at_office = days_at_home = 0
        total_worked_days = vacation_days = 0
        all_daily_summaries: list[str] = []

        for day_num in range(1, last_day + 1):
            current_day = datetime(year, month, day_num)
            is_weekend = current_day.weekday() >= 5

            week_folder = FileService.get_week_folder(base_dir, current_day)
            daily_notes_name = TimeService.get_daily_notes_name(current_day)
            daily_file_path = join(week_folder, daily_notes_name)

            if exists(daily_file_path):
                total_worked_days += 1
                stats = self._process_daily_file(daily_file_path)
                total_time_seconds += stats["time_seconds"]
                if stats["is_office"]:
                    days_at_office += 1
                elif stats["is_home"]:
                    days_at_home += 1
                all_daily_summaries.extend(stats["summary_lines"])
            elif not is_weekend:
                vacation_days += 1

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_time_seconds": total_time_seconds,
            "total_worked_days": total_worked_days,
            "vacation_days": vacation_days,
            "days_at_office": days_at_office,
            "days_at_home": days_at_home,
            "daily_summaries": all_daily_summaries,
        }

    def get_quarter_stats(self, custom_date: datetime, base_dir: str) -> dict[str, Any]:
        year = custom_date.year
        quarter_num = (custom_date.month - 1) // 3 + 1
        start_month = (quarter_num - 1) * 3 + 1
        end_month = start_month + 2
        _, last_day = monthrange(year, end_month)
        start_date = datetime(year, start_month, 1)
        end_date = datetime(year, end_month, last_day)

        total_time_seconds = days_at_office = days_at_home = 0
        total_worked_days = vacation_days = 0
        all_daily_summaries: list[str] = []

        current = start_date
        while current <= end_date:
            is_weekend = current.weekday() >= 5
            week_folder = FileService.get_week_folder(base_dir, current)
            daily_notes_name = TimeService.get_daily_notes_name(current)
            daily_file_path = join(week_folder, daily_notes_name)

            if exists(daily_file_path):
                total_worked_days += 1
                stats = self._process_daily_file(daily_file_path)
                total_time_seconds += stats["time_seconds"]
                if stats["is_office"]:
                    days_at_office += 1
                elif stats["is_home"]:
                    days_at_home += 1
                all_daily_summaries.extend(stats["summary_lines"])
            elif not is_weekend:
                vacation_days += 1

            current += timedelta(days=1)

        return {
            "quarter_num": quarter_num,
            "year": year,
            "start_date": start_date,
            "end_date": end_date,
            "total_time_seconds": total_time_seconds,
            "total_worked_days": total_worked_days,
            "vacation_days": vacation_days,
            "days_at_office": days_at_office,
            "days_at_home": days_at_home,
            "daily_summaries": all_daily_summaries,
        }

    def get_year_stats(self, year: int, base_dir: str) -> dict[str, Any]:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)

        total_time_seconds = days_at_office = days_at_home = 0
        total_worked_days = vacation_days = 0
        all_daily_summaries: list[str] = []

        current = start_date
        while current <= end_date:
            is_weekend = current.weekday() >= 5
            week_folder = FileService.get_week_folder(base_dir, current)
            daily_notes_name = TimeService.get_daily_notes_name(current)
            daily_file_path = join(week_folder, daily_notes_name)

            if exists(daily_file_path):
                total_worked_days += 1
                stats = self._process_daily_file(daily_file_path)
                total_time_seconds += stats["time_seconds"]
                if stats["is_office"]:
                    days_at_office += 1
                elif stats["is_home"]:
                    days_at_home += 1
                all_daily_summaries.extend(stats["summary_lines"])
            elif not is_weekend:
                vacation_days += 1

            current += timedelta(days=1)

        return {
            "year": year,
            "start_date": start_date,
            "end_date": end_date,
            "total_time_seconds": total_time_seconds,
            "total_worked_days": total_worked_days,
            "vacation_days": vacation_days,
            "days_at_office": days_at_office,
            "days_at_home": days_at_home,
            "daily_summaries": all_daily_summaries,
        }
