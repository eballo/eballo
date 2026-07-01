from dataclasses import dataclass, field

from taskjournal.models.task import Task


@dataclass
class ParsedNote:
    sprint_name: str = ""
    date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    breaks: list[str] = field(default_factory=list)
    time_spent: str = ""
    work_from: str = ""
    planned_tasks: list[Task] = field(default_factory=list)
    code_review_tasks: list[Task] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    summary: list[str] = field(default_factory=list)
    firefighter: list[str] = field(default_factory=list)
