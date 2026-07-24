from datetime import date, datetime, timedelta
from os import makedirs
from os.path import dirname, exists, join

from taskjournal.config import BASE_DIR, TEMPLATE_FORMAT
from taskjournal.constants import (
    WORKDAY_BREAK_HOURS_FRIDAY,
    WORKDAY_BREAK_HOURS_MON_TO_THU,
    WORKDAY_HOURS_FRIDAY,
    WORKDAY_HOURS_IF_HOLIDAY,
    WORKDAY_HOURS_MON_TO_THU,
)
from taskjournal.services.base import BaseService
from taskjournal.services.file import FileService
from taskjournal.services.logger import logger
from taskjournal.services.utils import FormatUtils


class TimeService(BaseService):

    def __init__(self) -> None:
        pass

    @staticmethod
    def calculate_working_hours(
        daily_notes_file: str,
    ) -> tuple[datetime | None, float | None, datetime | None]:
        try:
            lines = FileService.get_lines(daily_notes_file)
            _, created_time = TimeService.get_start_time(lines)
            elapsed_hours = (datetime.now() - created_time).total_seconds() / 3600
            week_folder = dirname(daily_notes_file)
            accumulated_seconds = TimeService.get_accumulated_week_seconds(week_folder, created_time)
            finish_time = TimeService.estimated_finish_time(created_time, week_folder, accumulated_seconds)
            return created_time, elapsed_hours, finish_time
        except Exception as e:
            logger.error(f"Error calculating working hours: {e}")
            return None, None, None

    @staticmethod
    def seconds_to_hours_minutes(total_seconds: int) -> tuple[int, int]:
        hours, remainder = divmod(int(total_seconds), 3600)
        minutes, _ = divmod(remainder, 60)
        return hours, minutes

    @staticmethod
    def get_total_time_spent(
        created_time: datetime, final_time: datetime, breaks_seconds: int = 3600
    ) -> tuple[int, int]:
        total_seconds = max(0, int((final_time - created_time).total_seconds()) - breaks_seconds)
        return TimeService.seconds_to_hours_minutes(total_seconds)

    @staticmethod
    def get_total_time_from_daily_notes(daily_file_path: str) -> int:
        total_time = 0
        time_spent_marker = FormatUtils.wrap_with_format("Time Spent:")
        with open(daily_file_path, "r") as file:
            for line in file:
                if line.startswith(time_spent_marker):
                    try:
                        time_str = line.replace(time_spent_marker, "").strip().split(".")[0]
                        h, m = map(int, time_str.split(":"))
                        total_time += h * 3600 + m * 60
                    except (ValueError, IndexError):
                        continue
        return total_time

    @staticmethod
    def get_holiday_notes_name(date: datetime | date) -> str:
        return date.strftime("%Y-%m-%d") + f"-DailyNotes-Holidays.{TEMPLATE_FORMAT}"

    @staticmethod
    def is_holiday_note(week_folder: str, day: datetime | date) -> bool:
        return exists(join(week_folder, TimeService.get_holiday_notes_name(day)))

    @staticmethod
    def get_holiday_equivalent_seconds() -> int:
        return int(WORKDAY_HOURS_IF_HOLIDAY * 3600)

    @staticmethod
    def get_accumulated_week_seconds(week_folder: str, today: datetime) -> int:
        start_of_week = today - timedelta(days=today.weekday())
        total = 0
        for i in range(min(today.weekday(), 5)):  # Mon up to (not including) today, max Fri
            day = start_of_week + timedelta(days=i)
            if TimeService.is_holiday_note(week_folder, day):
                total += TimeService.get_holiday_equivalent_seconds()
                continue
            daily_file = join(week_folder, TimeService.get_daily_notes_name(day))
            if exists(daily_file):
                try:
                    total += TimeService.get_total_time_from_daily_notes(daily_file)
                except Exception:
                    continue
        return total

    @staticmethod
    def get_expected_workday_seconds(day: datetime | date) -> int:
        hours = WORKDAY_HOURS_FRIDAY if day.weekday() == 4 else WORKDAY_HOURS_MON_TO_THU
        return int(hours * 3600)

    @staticmethod
    def get_expected_break_seconds(day: datetime | date) -> int:
        hours = WORKDAY_BREAK_HOURS_FRIDAY if day.weekday() == 4 else WORKDAY_BREAK_HOURS_MON_TO_THU
        return int(hours * 3600)

    @staticmethod
    def get_expected_week_seconds_before(week_folder: str, today: datetime) -> int:
        start_of_week = today - timedelta(days=today.weekday())
        days_before_today = min(today.weekday(), 5)  # Mon..Fri, capped for weekend notes
        total = 0
        for i in range(days_before_today):
            day = start_of_week + timedelta(days=i)
            if TimeService.is_holiday_note(week_folder, day):
                total += TimeService.get_holiday_equivalent_seconds()
            else:
                total += TimeService.get_expected_workday_seconds(day)
        return total

    @staticmethod
    def estimated_finish_time(
        created_time: datetime,
        week_folder: str,
        accumulated_seconds: int = 0,
    ) -> datetime:
        expected_seconds = TimeService.get_expected_week_seconds_before(week_folder, created_time)
        extra_seconds = accumulated_seconds - expected_seconds
        today_seconds = TimeService.get_expected_workday_seconds(created_time)
        today_work_seconds = min(today_seconds, max(0, today_seconds - extra_seconds))
        break_seconds = TimeService.get_expected_break_seconds(created_time)
        return created_time + timedelta(seconds=today_work_seconds + break_seconds)

    @staticmethod
    def get_start_time(lines: list[str]) -> tuple[int, datetime]:
        date = ""
        for i, line in enumerate(lines):
            if line.startswith(FormatUtils.wrap_with_format("Date:")):
                date = line.split(FormatUtils.wrap_with_format("Date:"))[1].strip()
            if line.startswith(FormatUtils.wrap_with_format("Start Time:")):
                created_line_index = i
                time = line.split(FormatUtils.wrap_with_format("Start Time:"))[1].strip()
                created_time = datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M:%S")
                break
        else:
            raise ValueError("Creation date not found in the file.")
        return created_line_index, created_time

    @staticmethod
    def get_daily_notes_name(date: datetime | date) -> str:
        return date.strftime("%Y-%m-%d") + f"-DailyNotes.{TEMPLATE_FORMAT}"

    @staticmethod
    def get_1on1_name(date: datetime | date) -> str:
        return date.strftime("%Y-%m-%d") + f"-1on1.{TEMPLATE_FORMAT}"

    @staticmethod
    def resolve_daily_notes_file(today: datetime) -> tuple[str, str]:
        """Return (daily_notes_file, week_folder) without creating any directories."""
        week_folder = FileService.get_week_folder(BASE_DIR, today)
        daily_notes_name = TimeService.get_daily_notes_name(today)
        daily_notes_file = join(week_folder, daily_notes_name)
        return daily_notes_file, week_folder

    @staticmethod
    def get_week_folder_and_daily_notes_file(today: datetime) -> tuple[str, str]:
        daily_notes_file, week_folder = TimeService.resolve_daily_notes_file(today)
        makedirs(week_folder, exist_ok=True)
        return daily_notes_file, week_folder
