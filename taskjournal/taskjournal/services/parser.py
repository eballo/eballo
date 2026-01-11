import os
import re
from typing import List, Any, Literal

from taskjournal.models.task import Status, Task
from taskjournal.services.logger import logger


class ParserService:
    def parse(self, content: str) -> dict:
        raise NotImplementedError()


class DailyParserService(ParserService):
    def __init__(self):
        self.meta_regex = {
            "sprint_name": re.compile(r"^\s*Sprint(?:[:\s]+)(.*)", re.IGNORECASE),
            "date": re.compile(r"^\s*Date:\s*(.*)", re.IGNORECASE),
            "start_time": re.compile(r"^\s*Start Time:\s*(.*)", re.IGNORECASE),
            "end_time": re.compile(
                r"^\s*(?:End Time|Finalized):\s*(.*)", re.IGNORECASE
            ),
            "time_spent": re.compile(
                r"^\s*(?:Total\s+)?Time Spent:\s*(.*)", re.IGNORECASE
            ),
            "work_from": re.compile(r"^\s*Work from:\s*(.*)", re.IGNORECASE),
        }
        # Regex for tasks in .txt format: [ ] Description or [x] Description
        self.task_regex_txt = re.compile(r"^\[([ xX-])\]\s*(.*)")
        self.task_regex_md = re.compile(r"^\s*-\s*\[([ xX-])\]\s*(.*)")

    def parse(self, file_path: str) -> dict:
        try:
            _, extension = os.path.splitext(file_path)
            lines = self._get_lines(file_path)
            data = self._parse_content(lines, extension)
            return data
        except Exception as e:
            logger.error(f"Failed to parse daily notes {file_path}: {e}")

    @staticmethod
    def _get_lines(file_path: str) -> list[str]:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines

    def _parse_content(self, lines: List[str], format_extension: str) -> dict:
        data = {
            "sprint_name": "",
            "date": None,
            "start_time": None,
            "end_time": None,
            "time_spent": "",
            "work_from": "",
            "planned_tasks": [],
            "code_review_tasks": [],
            "notes": [],
            "summary": [],
            "firefighter": [],
        }

        current_section = "metadata"

        for line in lines:
            line_stripped = line.strip()

            # 1. Detect Sections
            if "Planned Tasks" in line or "Tasks:" in line:
                current_section = "planned_tasks"
                continue
            elif "Code Review Tasks" in line:
                current_section = "code_review_tasks"
                continue
            elif "Notes" in line or "Work Notes:" in line:
                current_section = "notes"
                continue
            elif "Summary" in line:
                current_section = "summary"
                continue
            elif "Firefighter" in line:
                current_section = "firefighter"
                continue

            # 2. Parse Metadata
            if current_section == "metadata":
                for key, regex in self.meta_regex.items():
                    match = regex.match(line_stripped)
                    if match:
                        data[key] = match.group(1).strip()
                        break

            # 3. Parse Content based on section
            if current_section in ["planned_tasks", "code_review_tasks"]:
                self._parse_tasks(
                    current_section, data, line_stripped, format_extension
                )

            elif current_section in ["notes", "summary", "firefighter"]:
                # Preserve empty lines for notes and summary
                if line_stripped:
                    data[current_section].append(line_stripped)
                elif not data[current_section]:
                    # Don't add leading empty lines
                    pass
                else:
                    # Add newline to preserve paragraph structure
                    data[current_section].append("")

        return data

    def _parse_tasks(
        self,
        current_section: Literal["planned_tasks", "code_review_tasks"],
        data: dict[str | Any, str | None | list[Any] | Any],
        line_stripped: str,
        format_extension: str,
    ):
        if format_extension == ".md":
            task_match = self.task_regex_md.match(line_stripped)
        else:
            task_match = self.task_regex_txt.match(line_stripped)

        if task_match:
            status_char = task_match.group(1).lower()
            description = task_match.group(2)

            status = Status.TODO
            if status_char == "x":
                status = Status.DONE
            elif status_char == "-":
                status = Status.BLOCKED

            # Create Task object
            task = Task(
                id="legacy",  # ID doesn't matter for migration
                key=None,
                description=description,
                status=status,
            )
            data[current_section].append(task)
