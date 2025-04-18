from datetime import datetime, timedelta

from taskjournal.services.logger import logger


def calculate_working_hours(daily_notes_file: str):
    try:
        with open(daily_notes_file, "r") as file:
            for line in file:
                if line.startswith("Start time:"):
                    created_time = datetime.strptime(
                        line.split("Start time:")[1].strip(), "%Y-%m-%d %H:%M:%S"
                    )
                    break
            else:
                logger.warning("No 'Created' timestamp found in the file.")
                return None, None, None
        elapsed_hours = (datetime.now() - created_time).total_seconds() / 3600
        finish_time = created_time + timedelta(hours=9)
        return created_time, elapsed_hours, finish_time
    except Exception as e:
        logger.error(f"Error calculating working hours: {e}")
        return None, None, None


def get_total_time_from_daily_notes(daily_file_path: str) -> int:
    """Extract total time spent from a daily notes file."""
    total_time = 0

    with open(daily_file_path, "r") as file:
        for line in file:
            if line.startswith("Total Time Spent:"):
                try:
                    # Assuming the time is logged as "Time Spent: X hours Y minutes"
                    time_str = (
                        line.replace("Total Time Spent:", "").strip().split(".")[0]
                    )  # Ignore microseconds
                    h, m, s = map(int, time_str.split(":"))
                    total_time += h * 3600 + m * 60 + s
                except (ValueError, IndexError):
                    continue

    return total_time


def estimated_finish_time(created_time: datetime) -> datetime:
    # Estimate finish time (assuming an 8-hour workday)
    workday_hours = 9
    finish_time = created_time + timedelta(hours=workday_hours)
    return finish_time


def get_start_time(lines: list[str]) -> tuple[int, datetime]:
    # Find the creation date line
    for i, line in enumerate(lines):
        if line.startswith("Start time:"):
            created_line_index = i
            created_time = datetime.strptime(
                line.split("Start time:")[1].strip(), "%Y-%m-%d %H:%M:%S"
            )
            break
    else:
        raise ValueError("Creation date not found in the file.")
    return created_line_index, created_time
