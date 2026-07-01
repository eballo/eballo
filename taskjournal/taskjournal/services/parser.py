from os.path import splitext
from re import compile, IGNORECASE, Pattern
from typing import Literal
from uuid import uuid4

from taskjournal.constants import (
    SECTION_CODE_REVIEW_TASKS,
    SECTION_FIREFIGHTER,
    SECTION_NOTES,
    SECTION_PLANNED_TASKS,
    SECTION_SUMMARY,
)
from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Status, Task
from taskjournal.services.base import BaseService
from taskjournal.services.logger import logger

# Section detection rules — order matters: more specific patterns first
_SECTION_RULES: list[tuple[str, Pattern[str]]] = [
    ("code_review_tasks", compile(rf"^(?:#+.*{SECTION_CODE_REVIEW_TASKS}|🔍)", IGNORECASE)),
    ("planned_tasks",     compile(rf"^(?:#+.*{SECTION_PLANNED_TASKS}|Tasks:\s*$|✅)", IGNORECASE)),
    ("notes",             compile(rf"^(?:#+.*\b{SECTION_NOTES}\b|✍|Work\s+Notes:)", IGNORECASE)),
    ("summary",           compile(rf"^(?:#+.*\b{SECTION_SUMMARY}\b|📋|{SECTION_SUMMARY}:\s*$)", IGNORECASE)),
    ("firefighter",       compile(rf"^(?:#+.*{SECTION_FIREFIGHTER}|🚒)", IGNORECASE)),
]

_STATUS_CHAR_MAP: dict[str, Status] = {
    " ": Status.TODO,
    "x": Status.DONE,
    "-": Status.BLOCKED,
    ">": Status.IN_PROGRESS,
    "~": Status.CODE_REVIEW,
}


class ParserService(BaseService):
    def parse(self, file_path: str) -> ParsedNote | None:
        raise NotImplementedError()


class DailyParserService(ParserService):
    def __init__(self) -> None:
        self.meta_regex = {
            "sprint_name": compile(
                r"^\s*(?:\*\*)?Sprint(?:\*\*)?(?:[:\s\*]+)(.*?)(?:\*\*)?\s*$",
                IGNORECASE,
            ),
            "date": compile(
                r"^\s*(?:\*\*)?Date(?:\*\*)?[:\s\*]+(.*?)(?:\*\*)?\s*$", IGNORECASE
            ),
            "start_time": compile(
                r"^\s*(?:\*\*)?Start Time(?:\*\*)?[:\s\*]+(.*?)(?:\*\*)?\s*$",
                IGNORECASE,
            ),
            "end_time": compile(
                r"^\s*(?:\*\*)?(?:End Time|Finalized)(?:\*\*)?[:\s\*]+(.*?)(?:\*\*)?\s*$",
                IGNORECASE,
            ),
            "time_spent": compile(
                r"^\s*(?:\*\*)?(?:Total\s+)?Time Spent(?:\*\*)?[:\s\*]+(.*?)(?:\*\*)?\s*$",
                IGNORECASE,
            ),
            "work_from": compile(
                r"^\s*(?:\*\*)?Work from(?:\*\*)?[:\s\*]+(.*?)(?:\*\*)?\s*$",
                IGNORECASE,
            ),
        }
        self.break_regex = compile(
            r"^\s*(?:\*\*)?Break(?:\*\*)?[:\s\*]+(\d{1,2}:\d{2})\b",
            IGNORECASE,
        )
        # Regex for tasks — supports: [ ] TODO [x] DONE [-] BLOCKED [>] IN_PROGRESS [~] CODE_REVIEW
        self.task_regex_txt = compile(r"^\[([ xX>~-])\]\s*(.*)")
        self.task_regex_md = compile(r"^\s*-\s*\[([ xX>~-])\]\s*(.*)")

    def parse(self, file_path: str) -> ParsedNote | None:
        try:
            _, extension = splitext(file_path)
            lines = self._get_lines(file_path)
            return self._parse_content(lines, extension)
        except Exception as e:
            logger.error(f"Failed to parse daily notes {file_path}: {e}")
            return None

    @staticmethod
    def _get_lines(file_path: str) -> list[str]:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines

    def _parse_content(self, lines: list[str], format_extension: str) -> ParsedNote:
        note = ParsedNote()
        current_section = "metadata"

        for line in lines:
            line_stripped = line.strip()

            section_switched = False
            for section_name, pattern in _SECTION_RULES:
                if pattern.match(line_stripped):
                    current_section = section_name
                    section_switched = True
                    break
            if section_switched:
                continue

            if current_section == "metadata":
                break_match = self.break_regex.match(line_stripped)
                if break_match:
                    note.breaks.append(break_match.group(1).strip())
                    continue
                for key, regex in self.meta_regex.items():
                    match = regex.match(line_stripped)
                    if match:
                        setattr(note, key, match.group(1).strip())
                        break

            if current_section == "planned_tasks":
                self._parse_tasks("planned_tasks", note, line_stripped, format_extension)
            elif current_section == "code_review_tasks":
                self._parse_tasks("code_review_tasks", note, line_stripped, format_extension)
            elif current_section in ("notes", "summary", "firefighter"):
                section_list: list[str] = getattr(note, current_section)
                if line_stripped and line_stripped != "---":
                    section_list.append(line_stripped)
                elif not line_stripped and len(section_list) > 0:
                    section_list.append("")

        return note

    def _parse_tasks(
        self,
        current_section: Literal["planned_tasks", "code_review_tasks"],
        note: ParsedNote,
        line_stripped: str,
        format_extension: str,
    ) -> None:
        if format_extension == ".md":
            task_match = self.task_regex_md.match(line_stripped)
        else:
            task_match = self.task_regex_txt.match(line_stripped)

        if task_match:
            status_char = task_match.group(1).lower()
            description = task_match.group(2)
            status = _STATUS_CHAR_MAP.get(status_char, Status.TODO)
            task = Task(id=str(uuid4()), key=None, description=description, status=status)
            section_list: list[Task] = getattr(note, current_section)
            section_list.append(task)
