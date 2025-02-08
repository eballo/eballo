import os
from datetime import datetime

from service.logger import logger


def write_file(file_path: str, content: str, mode: str = "w") -> None:
    with open(file_path, mode) as file:
        file.write(content)

def load_template(template_path: str) -> str:
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found at {template_path}")
    with open(template_path, "r") as template_file:
        return template_file.read()

def append_template_to_file(template_content: str, file_path: str) -> None:
    with open(file_path, 'a') as target_file:
        target_file.write(template_content)


def check_finalized_in_file(file_path: str) -> bool:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                if 'Finalized:' in line:
                    return True
        return False
    except FileNotFoundError:
        logger.error(f"Error: The file '{file_path}' was not found.")
        return False
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return False

def get_week_folder(base_dir:str, date:datetime)-> str:
    """Calculate the folder path for the given date."""
    year = date.year
    week_num = date.isocalendar()[1]
    week_folder = os.path.join(base_dir, f"{year}", f"week{week_num}")
    return week_folder