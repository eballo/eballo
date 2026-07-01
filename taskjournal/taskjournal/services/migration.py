from dataclasses import asdict
from datetime import datetime
from re import search

from jinja2 import Template

from taskjournal.config import DAILY_NOTES_TEMPLATE
from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Task, Status
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.base import BaseService
from taskjournal.services.file import FileService
from taskjournal.services.logger import logger
from taskjournal.services.parser import DailyParserService
from taskjournal.services.task_manager import TaskManager
from taskjournal.services.time import TimeService
class MigrationService(BaseService):
    def __init__(
        self,
        task_formatter: TaskFormatter,
        parser: DailyParserService,
        task_manager: TaskManager,
    ) -> None:
        self.task_formatter = task_formatter
        self.daily_parser_service = parser
        self.task_manager = task_manager
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
            note = self.daily_parser_service.parse(file_path)
            if note is None:
                logger.error(f"Failed to parse daily notes {file_path}")
                return
            logger.debug(str(asdict(note)))

            date = self._extract_datetime_object(file_path)
            if date is None:
                logger.error(f"Failed to extract date from {file_path}")
                return
            md_content = self._generate_md_content(note, date)

            # Define new filename
            new_file_path = file_path.replace(".txt", ".md")

            # Write new file
            with open(new_file_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            logger.info(f"✅ Successfully created {new_file_path}")
            self.statistics["migrated_files"] += 1

        except Exception as e:
            logger.error(f"Failed to migrate {file_path}: {e}")

    @staticmethod
    def _extract_datetime_object(file_path: str) -> datetime | None:
        # 1. Find the date pattern (YYYY-MM-DD)
        match = search(r"(\d{4}-\d{2}-\d{2})", file_path)

        if match:
            date_string = match.group(1)  # Extracts "2025-01-10"

            # 2. Convert string to a datetime object
            # %Y = 4-digit year, %m = 2-digit month, %d = 2-digit day
            dt_object = datetime.strptime(date_string, "%Y-%m-%d")
            return dt_object
        return None

    def _generate_md_content(self, note: ParsedNote, date: datetime) -> str:
        work_from = self.task_manager.get_work_from_location(date)
        template_content = FileService.load_template(DAILY_NOTES_TEMPLATE)

        start_date_time = note.start_time if note.start_time else "09:00:00"
        end_date_time = note.end_time if note.end_time else self._get_end_time(date)

        daily_notes_content = Template(template_content).render(
            day_name=date.strftime("%A"),
            sprint_name=note.sprint_name if note.sprint_name else "No active sprint",
            date=note.date if note.date else date.strftime("%Y-%m-%d"),
            start_time=start_date_time,
            end_time=end_date_time,
            time_spent=(
                note.time_spent
                if note.time_spent
                else self._calculate_time_spent(start_date_time, end_date_time)
            ),
            work_from=work_from,
            tasks=self.task_formatter.format_tasks(note.planned_tasks, with_name=True),
            code_review_tasks=self.task_formatter.format_tasks(
                note.code_review_tasks, with_name=True,
            ),
            notes="\n".join(note.notes),
            summary="\n".join(note.summary),
            firefighter=bool(note.firefighter),
            firefighter_notes="\n".join(note.firefighter) if note.firefighter else "",
            extra="\n **NOTE:** This daily note was migrated from a legacy .txt format. For more information, check the txt file.",
        )

        return daily_notes_content

    @staticmethod
    def _get_end_time(date: datetime) -> str:
        if date.strftime("%A") != "Friday":
            return "18:30:00"
        return "14:00:00"

    @staticmethod
    def _format_md_task(task: Task) -> str:
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
    def _calculate_time_spent(start_date_time: str, end_date_time: str) -> str:
        try:

            def _parse_time(value: str) -> datetime:
                for fmt in ("%H:%M", "%H:%M:%S"):
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
                raise ValueError(f"Unsupported time format: {value}")

            start_dt = _parse_time(start_date_time)
            end_dt = _parse_time(end_date_time)
            total_seconds = int((end_dt - start_dt).total_seconds())
            hours, minutes = TimeService.seconds_to_hours_minutes(total_seconds)
            return f"{hours:02}:{minutes:02}"
        except Exception as e:
            logger.warning(f"Failed to calculate time spent: {e}")
            return "08:30"  # Default to 8.5 hours
