import os
from datetime import datetime


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

def create_daily_notes_file(file_path: str, template_path: str) -> None:
    """Create a daily file using a template and adding a creation timestamp.

    Args:
        file_path (str): The path for the new daily notes file.
        template_path (str): The path to the template file.
    """
    # Load the template content
    try:
        with open(template_path, "r") as template_file:
            template_content = template_file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Template file not found at {template_path}")

    # Add timestamp to the content
    creation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    daily_notes_content = template_content.replace("{{creation_time}}", creation_time)

    # Add default tasks with [ ] placeholders
    default_tasks = "\n".join(["[ ] Check emails", "[ ] Attend stand-up", "[ ] Plan tasks"])
    daily_notes_content = daily_notes_content.replace("{{tasks}}", default_tasks)

    # Write the daily notes file
    write_file(file_path, daily_notes_content)


def finalize_daily_notes(file_path:str) -> None:
    """Add a final timestamp to the daily notes file."""
    final_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(file_path, "a") as file:
        file.write(f"\nFinalized: {final_time}\n")


def create_week_summary(week_folder: str) -> None:
    """Create a week summary file."""
    summary_file = os.path.join(week_folder, "week-summary.txt")
    if not os.path.exists(summary_file):
        write_file(summary_file, "==== Weekly Summary ===\n\n")
    # Aggregate daily notes into the week summary
    for file_name in sorted(os.listdir(week_folder)):
        if file_name.endswith("-DailyNotes.txt"):
            with open(os.path.join(week_folder, file_name), "r") as daily_file:
                daily_content = daily_file.read()
            write_file(summary_file, f"\n{file_name}:\n{daily_content}\n", mode="a")



def create_retro_file(week_folder):
    """Create a retro file."""
    retro_file = os.path.join(week_folder, "retro.txt")
    if not os.path.exists(retro_file):
        with open(retro_file, "w") as file:
            file.write("==== Retro ===\n\n")
    return retro_file