import uuid
from typing import Literal

from taskjournal.config import TEMPLATE_FORMAT
from taskjournal.constants import NORMAL_TASKS
from taskjournal.models.task import Task, Status


class ParseFile:

    def __init__(self):
        self.prefix = "" if TEMPLATE_FORMAT == "txt" else " - "

    def get_tasks(self, lines: list[str]) -> list[Task]:
        tasks = []
        for line in lines:
            if line.startswith(self.prefix + "["):
                description = line[4:].strip()
                if description in NORMAL_TASKS:
                    # Skip tasks that are not in the normal task list
                    continue
                task = Task(
                    id=str(uuid.uuid4()),
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
