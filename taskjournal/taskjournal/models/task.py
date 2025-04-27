from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Status(str, Enum):
    DONE = "done"  # [x]
    NOT_FINISHED = "not_finished"  # [ ]
    IN_PROGRESS = "in_progress"  # [->]
    BLOCKED = "blocked"  # [-]
    INACTIVE = "inactive"  # [!]


class Task(BaseModel):
    id: str
    description: str
    status: Status = Status.NOT_FINISHED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def __str__(self):
        return f" - {self.description}"
