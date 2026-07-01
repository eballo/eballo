from datetime import datetime
from os import makedirs
from os.path import exists, join
from re import compile as re_compile, Pattern

from taskjournal.config import BASE_DIR
from taskjournal.models.task import Task
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.file import FileService
from taskjournal.services.logger import logger
from taskjournal.services.parser import DailyParserService, _SECTION_RULES
from taskjournal.services.time import TimeService


class TaskCommands:

    def __init__(
        self,
        parser: DailyParserService,
        file_service: FileService,
        time_service: TimeService,
        task_formatter: TaskFormatter,
    ) -> None:
        self.parser = parser
        self.file_service = file_service
        self.time_service = time_service
        self.task_formatter = task_formatter

    def _get_daily_notes_file_path(self, today: datetime) -> str:
        week_folder = self.file_service.get_week_folder(BASE_DIR, today)
        makedirs(week_folder, exist_ok=True)
        return join(week_folder, self.time_service.get_daily_notes_name(today))

    def list_tasks_in_daily(self, date: datetime) -> list[Task]:
        file_path = self._get_daily_notes_file_path(date)
        if not exists(file_path):
            return []
        note = self.parser.parse(file_path)
        return note.planned_tasks if note else []

    def add_task_to_daily(self, date: datetime, description: str) -> None:
        file_path = self._get_daily_notes_file_path(date)
        if not exists(file_path):
            raise FileNotFoundError(f"No daily notes for {date.strftime('%Y-%m-%d')}")

        ext = ".md" if file_path.endswith(".md") else ".txt"
        lines = self.file_service.get_lines(file_path)
        task_rx: Pattern[str] = re_compile(r"^\s*-?\s*\[[ xX>~-]\]")

        in_planned = False
        last_task_idx = -1
        section_header_idx = -1

        for i, raw in enumerate(lines):
            stripped = raw.strip()
            for sec_name, pat in _SECTION_RULES:
                if pat.match(stripped):
                    in_planned = sec_name == "planned_tasks"
                    if in_planned:
                        section_header_idx = i
                    break
            if in_planned and task_rx.match(stripped):
                last_task_idx = i

        insert_at = last_task_idx if last_task_idx != -1 else section_header_idx
        if insert_at == -1:
            raise ValueError("Planned Tasks section not found in daily notes.")

        prefix = " - " if ext == ".md" else ""
        lines.insert(insert_at + 1, f"{prefix}[ ] {description}\n")
        self.file_service.write_lines_to_file(file_path, lines)
        logger.info(f"Task added: {description}")

    def _update_task_status(self, date: datetime, description: str, new_char: str) -> bool:
        file_path = self._get_daily_notes_file_path(date)
        if not exists(file_path):
            raise FileNotFoundError(f"No daily notes for {date.strftime('%Y-%m-%d')}")

        lines = self.file_service.get_lines(file_path)
        needle = description.strip().lower()
        task_rx: Pattern[str] = re_compile(r"\[([ xX>~-])\](\s*)(.*)")

        for i, raw in enumerate(lines):
            m = task_rx.search(raw)
            if m:
                task_text = m.group(3).strip().lower()
                if needle in task_text or task_text in needle:
                    lines[i] = raw.replace(f"[{m.group(1)}]", f"[{new_char}]", 1)
                    self.file_service.write_lines_to_file(file_path, lines)
                    return True

        return False

    def complete_task_in_daily(self, date: datetime, description: str) -> bool:
        return self._update_task_status(date, description, "x")

    def block_task_in_daily(self, date: datetime, description: str) -> bool:
        return self._update_task_status(date, description, "-")

    def wip_task_in_daily(self, date: datetime, description: str) -> bool:
        return self._update_task_status(date, description, ">")
