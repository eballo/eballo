import re
from datetime import datetime
from typing import List, Any, Tuple

from jinja2 import Template

from taskjournal.config import DAILY_NOTES_TEMPLATE
from taskjournal.models.task import Task, Status
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.file import load_template
from taskjournal.services.logger import logger
from taskjournal.services.task_manager import get_work_from_defaults
from taskjournal.services.time import get_total_time_spent


class MigrationService:
    def __init__(self):
        self.task_formatter = TaskFormatter()
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
        self.task_regex = re.compile(r"^\[([ xX-])\]\s*(.*)")
        self.statistics = {
            "migrated_files": 0,
            "skipped_files": 0,
        }

    def migration_info(self) -> None:
        logger.info("Migration Summary:")
        logger.info(f"  Migrated Files: {self.statistics['migrated_files']}")
        logger.info(f"  Skipped Files: {self.statistics['skipped_files']}")

    def migrate_file(self, file_path: str) -> None:
        if not file_path.endswith(".txt"):
            logger.warning(f"Skipping non-txt file: {file_path}")
            self.statistics["skipped_files"] += 1
            return

        logger.info(f"Migrating {file_path}...")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            data = self._parse_txt_content(lines)
            # print(json.dumps(data, indent=4, sort_keys=True))
            date = self._extract_datetime_object(file_path)
            md_content = self._generate_md_content(data, date)

            # Define new filename
            new_file_path = file_path.replace(".txt", ".md")

            # print(md_content)

            # Write new file
            with open(new_file_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            logger.info(f"✅ Successfully created {new_file_path}")
            self.statistics["migrated_files"] += 1

        except Exception as e:
            logger.error(f"Failed to migrate {file_path}: {e}")

    def _parse_txt_content(self, lines: List[str]) -> dict:
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

            # 2. Parse Metadata (only if in metadata section or top of file)
            if current_section == "metadata":
                for key, regex in self.meta_regex.items():
                    match = regex.match(line_stripped)
                    if match:
                        data[key] = match.group(1).strip()
                        break

            # 3. Parse Content based on section
            if current_section in ["planned_tasks", "code_review_tasks"]:
                task_match = self.task_regex.match(line_stripped)
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
                        description=description,
                        status=status,
                    )
                    data[current_section].append(task)

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

    def _extract_datetime_object(self, file_path: str) -> Any:
        # 1. Find the date pattern (YYYY-MM-DD)
        match = re.search(r"(\d{4}-\d{2}-\d{2})", file_path)

        if match:
            date_string = match.group(1)  # Extracts "2025-01-10"

            # 2. Convert string to a datetime object
            # %Y = 4-digit year, %m = 2-digit month, %d = 2-digit day
            dt_object = datetime.strptime(date_string, "%Y-%m-%d")
            return dt_object
        return None

    def _generate_md_content(self, data: dict, date: datetime) -> str:
        work_from = get_work_from_defaults(date)
        template_content = load_template(DAILY_NOTES_TEMPLATE)

        start_date_time = data["start_time"] if data["start_time"] else "09:00:00"
        end_date_time = (
            data["end_time"] if data["end_time"] else self._get_end_time(date)
        )

        daily_notes_content = Template(template_content).render(
            day_name=date.strftime("%A"),
            sprint_name=(
                data["sprint_name"] if data["sprint_name"] else "No active sprint"
            ),
            date=data["date"] if data["date"] else date.strftime("%Y-%m-%d"),
            start_time=start_date_time,
            end_time=end_date_time,
            time_spent=(
                data["time_spent"]
                if data["time_spent"]
                else self._calculate_time_spent(start_date_time, end_date_time)
            ),
            work_from=work_from,
            tasks=self.task_formatter.format_tasks(
                data["planned_tasks"], with_name=True
            ),
            code_review_tasks=self.task_formatter.format_tasks(
                data["code_review_tasks"],
                with_name=True,
            ),
            notes="\n".join(data["notes"]),
            summary="\n".join(data["summary"]),
            firefighter=True if data["firefighter"] else False,
            firefighter_notes=(
                "\n".join(data["firefighter"]) if data["firefighter"] else ""
            ),
            extra="\n **NOTE:** This daily note was migrated from a legacy .txt format. For more information, check the txt file.",
        )

        return daily_notes_content

    def _get_end_time(self, date: datetime) -> str:
        if date.strftime("%A") != "Friday":
            return "18:30:00"
        return "14:00:00"

    def _format_md_task(self, task: Task) -> str:
        # Manual formatting to MD style
        check = " "
        if task.status == Status.DONE:
            check = "x"
        elif task.status == Status.BLOCKED:
            check = "-"

        # We don't have task.github or task.link populated from regex usually,
        # unless we improved the regex to capture [BE-123](url).
        # For now, just dumping the description is safe.
        return f" - [{check}] {task.description}"

    @staticmethod
    def _calculate_time_spent(
        start_date_time: str, end_date_time: str
    ) -> Tuple[str, str]:
        try:
            start_dt = datetime.strptime(start_date_time, "%H:%M")
            end_dt = datetime.strptime(end_date_time, "%H:%M")
            hours, minutes = get_total_time_spent(start_dt, end_dt)
            return f"{hours:02}:{minutes}"
        except Exception as e:
            logger.warning(f"Failed to calculate time spent: {e}")
            return "08:30"  # Default to 8.5 hours
