import os
from datetime import datetime, timedelta

from taskjournal.config import BASE_DIR, TEMPLATE_FORMAT
from taskjournal.services.file import FileService
from taskjournal.services.logger import logger
from taskjournal.services.utils import FormatUtils


class TimeService:

    @staticmethod
    def calculate_working_hours(
        daily_notes_file: str,
    ) -> tuple[datetime | None, float | None, datetime | None]:
        try:
            lines = FileService.get_lines(daily_notes_file)
            _, created_time = TimeService.get_start_time(lines)
            elapsed_hours = (datetime.now() - created_time).total_seconds() / 3600
            finish_time = created_time + timedelta(hours=9)
            return created_time, elapsed_hours, finish_time
        except Exception as e:
            logger.error(f"Error calculating working hours: {e}")
            return None, None, None

    @staticmethod
    def get_total_time_spent(
        created_time: datetime, final_time: datetime
    ) -> tuple[int, int]:
        total_time_spent = final_time - created_time
        total_seconds = int(total_time_spent.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return hours, minutes

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
    def estimated_finish_time(created_time: datetime) -> datetime:
        """Estimate the finish time based on the created time."""
        workday_hours = 9
        return created_time + timedelta(hours=workday_hours)

    @staticmethod
    def get_start_time(lines: list[str]) -> tuple[int, datetime]:
        """Extract the start time from the daily notes file."""
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
    def get_daily_notes_name(date: datetime) -> str:
        return date.strftime("%Y-%m-%d") + f"-DailyNotes.{TEMPLATE_FORMAT}"

    @staticmethod
    def get_1on1_name(date: datetime) -> str:
        return date.strftime("%Y-%m-%d") + f"-1on1.{TEMPLATE_FORMAT}"

    @staticmethod
    def get_week_folder_and_daily_notes_file(today: datetime) -> tuple[str, str]:
        week_folder = FileService.get_week_folder(BASE_DIR, today)
        os.makedirs(week_folder, exist_ok=True)
        daily_notes_name = TimeService.get_daily_notes_name(today)
        daily_notes_file = os.path.join(week_folder, daily_notes_name)
        return daily_notes_file, week_folder
