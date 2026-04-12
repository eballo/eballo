import os
from datetime import datetime, date
from pathlib import Path

from taskjournal.services.logger import logger


class FileService:

    @staticmethod
    def get_lines(file_path: str) -> list[str]:
        with open(file_path, "r") as file:
            lines = file.readlines()
        return lines

    @staticmethod
    def write_to_file(file_path: str, content: str, mode: str = "w") -> None:
        with open(file_path, mode) as file:
            file.write(content)

    @staticmethod
    def write_lines_to_file(file_path: str, lines: list[str], mode: str = "w") -> None:
        with open(file_path, mode) as file:
            file.writelines(lines)

    @staticmethod
    def load_template(template_path: str) -> str:
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found at {template_path}")
        with open(template_path, "r") as template_file:
            return template_file.read()

    @staticmethod
    def check_finalized_in_file(file_path: str) -> bool:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    if "Finalized:" in line:
                        return True
            return False
        except FileNotFoundError:
            logger.error(f"Error: The file '{file_path}' was not found.")
            return False
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return False

    @staticmethod
    def get_week_folder(base_dir: str | Path, date_obj: datetime | date) -> str:
        """Calculate the folder path for the given date."""
        year = date_obj.year
        week_num = date_obj.isocalendar()[1]
        week_folder = os.path.join(base_dir, f"{year}", f"week{week_num}")
        return week_folder

    @staticmethod
    def get_summary_from_daily_notes(daily_file_path: str) -> str:
        with open(daily_file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("## 📋 Summary") or stripped == "📋 Summary":
                return "".join(lines[i + 1 :]).strip()

        return ""
