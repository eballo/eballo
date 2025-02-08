import os
from datetime import datetime
from service.logger import logger


def get_tasks_from_daily_notes(file_path: str):
    done_tasks, pending_tasks = [], []
    try:
        with open(file_path, "r") as daily_file:
            for line in daily_file:
                if line.startswith("[x]"):
                    done_tasks.append(line[4:].strip())
                elif line.startswith("[ ]"):
                    pending_tasks.append(line[4:].strip())
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
    return done_tasks, pending_tasks

def normalize_task(task: str) -> str:
    """Normalize a task by removing its checkbox prefix."""
    if task.startswith("[x]") or task.startswith("[ ]"):
        return task[4:].strip()
    return task.strip()

def get_default_tasks() -> list:
    """Return the default tasks based on the day of the week."""
    default_tasks = ["[ ] Check emails"]
    day_of_week = datetime.now().strftime("%A")

    if day_of_week == "Wednesday":
        default_tasks.extend(["[ ] Check refinement tasks"])
    elif day_of_week == "Thursday" and (datetime.now().isocalendar()[1] % 2 == 0):
        default_tasks.append("[ ] Get ready for the retro points")
    elif day_of_week == "Friday":
        default_tasks.append("[ ] Write down the summary of the week")

    return default_tasks

def get_previous_tasks(folder_path: str, current_file: str) -> list:
    """Retrieve unfinished tasks from the most recent daily notes file."""
    if not os.path.exists(folder_path):
        return []
    daily_files = [
        f for f in os.listdir(folder_path)
        if f.endswith(".txt") and f != current_file
    ]
    if not daily_files:
        return []
    latest_file = os.path.join(folder_path, sorted(daily_files, reverse=True)[0])
    try:
        with open(latest_file, "r") as file:
            return [line.strip() for line in file if line.strip().startswith("[ ]")]
    except Exception as e:
        logger.warning(f"Warning: Could not read previous file {latest_file}: {e}")
        return []