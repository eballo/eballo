from typing import Literal, TypedDict
from uuid import uuid4

from taskjournal.config import TEMPLATE_FORMAT
from taskjournal.constants import NORMAL_TASKS
from taskjournal.models.task import Task, Status


class FormatConfig(TypedDict):
    prefix: str
    size: int


FORMAT_CONFIG: dict[str, FormatConfig] = {
    "txt": {"prefix": "", "size": 4},
    "md": {"prefix": " - ", "size": 6},
}


class ParseFile:

    def __init__(self) -> None:
        config = FORMAT_CONFIG.get(TEMPLATE_FORMAT)
        if config is None:
            raise ValueError(f"Invalid TEMPLATE_FORMAT: {TEMPLATE_FORMAT}")
        self.prefix: str = config["prefix"]
        self.size: int = config["size"]

    def get_tasks(self, lines: list[str]) -> list[Task]:
        tasks = []
        for line in lines:
            if line.startswith(self.prefix + "["):
                description = line[self.size :].strip()
                if description in NORMAL_TASKS:
                    # Skip tasks that are not in the normal task list
                    continue
                task = Task(
                    id=str(uuid4()),
                    description=description,
                    status=self.get_task_status(line),
                )
                tasks.append(task)
        return tasks

    def get_task_status(
        self,
        line: str,
    ) -> Literal[Status.DONE, Status.TODO, Status.BLOCKED]:
        if line.startswith(self.prefix + "[x]"):
            return Status.DONE
        elif line.startswith(self.prefix + "[-]"):
            return Status.BLOCKED
        else:
            return Status.TODO
