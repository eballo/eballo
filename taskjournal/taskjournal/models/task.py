from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Status(str, Enum):
    TODO = "To Do"  # [ ]
    IN_PROGRESS = "In Progress"  # [ ]
    CODE_REVIEW = "Code Review"  # [ ]
    BLOCKED = "Blocked"  # [-]
    DONE = "Done"  # [x]


class Task(BaseModel):
    id: str
    key: Optional[str] = None
    description: str
    status: Status = Status.TODO
    link: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def __str__(self):
        key = f"[{self.key}]" if self.key else ""
        return f"{key}{self.description} ({self.status.value})"
