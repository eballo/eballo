import os
from datetime import datetime, timedelta

from taskjournal.config import BASE_DIR, TEMPLATE_FORMAT
from taskjournal.services.file import get_week_folder, get_lines
from taskjournal.services.logger import logger


def calculate_working_hours(daily_notes_file: str):
    try:
        lines = get_lines(daily_notes_file)
        _, created_time = get_start_time(lines)
        elapsed_hours = (datetime.now() - created_time).total_seconds() / 3600
        finish_time = created_time + timedelta(hours=9)
        return created_time, elapsed_hours, finish_time
    except Exception as e:
        logger.error(f"Error calculating working hours: {e}")
        return None, None, None


def get_total_time_from_daily_notes(daily_file_path: str) -> int:
    total_time = 0
    with open(daily_file_path, "r") as file:
        for line in file:
            if line.startswith(" Time Spent:"):
                try:
                    time_str = line.replace(" Time Spent:", "").strip().split(".")[0]
                    h, m = map(int, time_str.split(":"))
                    total_time += h * 3600 + m * 60
                except (ValueError, IndexError):
                    continue
    return total_time


def estimated_finish_time(created_time: datetime) -> datetime:
    """Estimate the finish time based on the created time"""
    workday_hours = 9
    finish_time = created_time + timedelta(hours=workday_hours)
    return finish_time


def get_start_time(lines: list[str]) -> tuple[int, datetime]:
    """Extract the start time from the daily notes file."""
    opening = " " if TEMPLATE_FORMAT == "txt" else "**"
    closing = "" if TEMPLATE_FORMAT == "txt" else "**"

    date = ""
    for i, line in enumerate(lines):
        if line.startswith(opening + "Date:" + closing):
            date = line.split(opening + "Date:" + closing)[1].strip()
        if line.startswith(opening + "Start Time:" + closing):
            created_line_index = i
            time = line.split(opening + "Start Time:" + closing)[1].strip()
            created_time = datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M:%S")
            break
    else:
        raise ValueError("Creation date not found in the file.")
    return created_line_index, created_time


def get_daily_notes_name(date: datetime) -> str:
    return date.strftime("%Y-%m-%d") + f"-DailyNotes.{TEMPLATE_FORMAT}"


def get_week_folder_and_daily_notes_file(today: datetime) -> tuple[str, str]:
    week_folder = get_week_folder(BASE_DIR, today)
    os.makedirs(week_folder, exist_ok=True)
    daily_notes_name = get_daily_notes_name(today)
    daily_notes_file = os.path.join(week_folder, daily_notes_name)
    return daily_notes_file, week_folder
