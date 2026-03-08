from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class User(BaseModel):
    name: str

    def __str__(self) -> str:
        return self.name


class Epic(BaseModel):
    key: str
    summary: str

    def __str__(self) -> str:
        key = f"[{self.key}]" if self.key else ""
        return f"{key}{self.summary}"


class Status(str, Enum):
    TODO = "To Do"  # [ ]
    IN_PROGRESS = "In Progress"  # [ ]
    CODE_REVIEW = "Code Review"  # [ ]
    BLOCKED = "Blocked"  # [-]
    DONE = "Done"  # [x]


class Task(BaseModel):
    id: str
    key: str | None = None
    description: str
    status: Status = Status.TODO
    link: str | None = None
    github: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    epic: Epic | None = None
    assignee: User | None = None

    def __str__(self) -> str:
        key = f"[{self.key}]" if self.key else ""
        return f"{key}{self.description} ({self.assignee})"
