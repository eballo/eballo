import os
from datetime import datetime, timedelta


def get_week_folder(base_dir:str, date:datetime)-> str:
    """Calculate the folder path for the given date."""
    year = date.year
    week_num = date.isocalendar()[1]
    week_folder = os.path.join(base_dir, f"{year}", f"week{week_num}")
    return week_folder


def write_file(file_path: str, content: str, mode: str = "w") -> None:
    """Write content to a file with the given mode."""
    with open(file_path, mode) as file:
        file.write(content)

def load_template(template_path: str) -> str:
    """Load the template content from the given path."""
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found at {template_path}")
    with open(template_path, "r") as template_file:
        return template_file.read()

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
        print(f"Warning: Could not read previous file {latest_file}: {e}")
        return []

def normalize_task(task: str) -> str:
    """Normalize a task by removing its checkbox prefix."""
    if task.startswith("[x]") or task.startswith("[ ]"):
        return task[4:].strip()
    return task.strip()

def get_tasks_from_daily_notes(file_path: str) -> tuple:
    """Extract done and pending tasks from a daily notes file."""
    done_tasks = []
    pending_tasks = []
    try:
        with open(file_path, "r") as daily_file:
            for line in daily_file:
                line = line.strip()
                if line.startswith("[x]"):
                    done_tasks.append(normalize_task(line))
                elif line.startswith("[ ]"):
                    pending_tasks.append(normalize_task(line))
    except Exception as e:
        print(f"Warning: Could not read daily file {file_path}: {e}")
    return done_tasks, pending_tasks

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

def get_total_time_from_daily_notes(daily_file_path: str) -> int:
    """Extract total time spent from a daily notes file."""
    total_time = 0

    with open(daily_file_path, 'r') as file:
        for line in file:
            if line.startswith("Total Time Spent:"):
                try:
                    # Assuming the time is logged as "Time Spent: X hours Y minutes"
                    time_str = line.replace("Total Time Spent:", "").strip().split(".")[0]  # Ignore microseconds
                    h, m, s = map(int, time_str.split(":"))
                    total_time += h * 3600 + m * 60 + s
                except (ValueError, IndexError):
                    continue

    return total_time

def calculate_working_hours(daily_notes_file:str) -> (str, str, str):
    """
    Calculate current working hours and estimated finish time based on the 'Created' timestamp
    in the daily notes file.
    """
    try:
        with open(daily_notes_file, "r") as file:
            for line in file:
                if line.startswith("Start time:"):
                    # Extract the timestamp from the line
                    created_time_str = line.split("Start time:")[1].strip()
                    created_time = datetime.strptime(created_time_str, "%Y-%m-%d %H:%M:%S")
                    break
            else:
                print("No 'Created' timestamp found in the file.")
                return None, None, None

        current_time = datetime.now()

        # Calculate elapsed hours
        elapsed_time = current_time - created_time
        elapsed_hours = elapsed_time.total_seconds() / 3600

        finish_time = estimated_finish_time(created_time)

        return created_time_str, elapsed_hours, finish_time

    except Exception as e:
        print(f"Error calculating working hours: {e}")
        return None, None


def estimated_finish_time(created_time):
    # Estimate finish time (assuming an 8-hour workday)
    workday_hours = 9
    finish_time = created_time + timedelta(hours=workday_hours)
    return finish_time


def create_daily_notes_file(file_path: str, template_path: str) -> None:
    """Create a daily file using a template and adding a creation timestamp.

    Args:
        file_path (str): The path for the new daily notes file.
        template_path (str): The path to the template file.
    """

    # Extract folder path
    folder_path = os.path.dirname(file_path)

    # Load template and add timestamp
    template_content = load_template(template_path)
    creation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    daily_notes_content = template_content.replace("{{creation_time}}", creation_time)

    # Get tasks: unfinished tasks + default tasks
    previous_tasks = get_previous_tasks(folder_path, os.path.basename(file_path))
    default_tasks = get_default_tasks()
    unique_tasks = list(dict.fromkeys(default_tasks + previous_tasks))
    daily_notes_content = daily_notes_content.replace("{{tasks}}", "\n".join(unique_tasks))

    # Write the daily notes file
    write_file(file_path, daily_notes_content)

    return estimated_finish_time(creation_time)


def finalize_daily_notes(file_path: str) -> None:
    """Add a final timestamp to the daily notes file and calculate total time spent."""
    with open(file_path, "r") as file:
        lines = file.readlines()

    # Find the creation date line
    for i, line in enumerate(lines):
        if line.startswith("Start time:"):
            created_line_index = i
            created_time = datetime.strptime(line.split("Start time:")[1].strip(), "%Y-%m-%d %H:%M:%S")
            break
    else:
        raise ValueError("Creation date not found in the file.")

    # Calculate finalized time and total time spent
    final_time = datetime.now()
    total_time_spent = final_time - created_time
    finalized_line = f"Finalized: {final_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    total_time_line = f"Total Time Spent: {total_time_spent}\n"

    # Insert finalized time and total time spent below the creation date
    lines.insert(created_line_index + 1, finalized_line)
    lines.insert(created_line_index + 2, total_time_line)

    # Write back the updated file
    with open(file_path, "w") as file:
        file.writelines(lines)


def create_week_summary(week_folder: str, template_path: str) -> None:
    """Create a week summary file."""
    summary_file = os.path.join(week_folder, "week-summary.txt")
    week_summary_content = load_template(template_path)
    done_tasks = []
    pending_tasks = []
    total_time_seconds = 0

    for file_name in sorted(os.listdir(week_folder)):
        if file_name.endswith("-DailyNotes.txt"):
            daily_file_path = os.path.join(week_folder, file_name)
            daily_done, daily_pending = get_tasks_from_daily_notes(daily_file_path)
            daily_time = get_total_time_from_daily_notes(daily_file_path)  # Extract total time from daily notes

            done_tasks.extend(daily_done)
            pending_tasks.extend(daily_pending)
            total_time_seconds += daily_time

    # Remove pending tasks that have been completed
    pending_tasks = [task for task in pending_tasks if task not in done_tasks]

    # Calculate total hours and minutes for the week
    total_hours, remainder = divmod(total_time_seconds, 3600)
    total_minutes, total_seconds = divmod(remainder, 60)

    week_summary_content = week_summary_content.replace("{{total_time}}", f" {total_hours} hours and {total_minutes} minutes")
    week_summary_content = week_summary_content.replace("{{done_tasks}}", "\n".join(f"[x] {task}" for task in done_tasks))
    week_summary_content = week_summary_content.replace("{{pending_tasks}}", "\n".join(f"[ ] {task}" for task in pending_tasks))
    week_summary_content = week_summary_content.replace("{{summary}}", "\nWrite your weekly summary here...\n")

    write_file(summary_file, week_summary_content)


def create_retro_file(week_folder: str, template_path: str) -> str:
    """Create a retro file using a template."""
    retro_file = os.path.join(week_folder, "retro.txt")

    if not os.path.exists(retro_file):
        template_content = load_template(template_path)
        with open(retro_file, "w") as file:
            file.write(template_content)

    return retro_file
