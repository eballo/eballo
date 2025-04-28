import uuid
from typing import Literal

from taskjournal.constants import NORMAL_TASKS
from taskjournal.models.task import Task, Status


def get_task_status(
    line: str,
) -> Literal[Status.DONE, Status.TODO, Status.BLOCKED]:
    if line.startswith("[x]"):
        return Status.DONE
    elif line.startswith("[-]"):
        return Status.BLOCKED
    else:
        return Status.TODO


class ParseFile:

    @staticmethod
    def get_tasks(lines: list[str]) -> list[Task]:
        tasks = []
        for line in lines:
            if line.startswith("["):
                description = line[4:].strip()
                if description in NORMAL_TASKS:
                    # Skip tasks that are not in the normal task list
                    continue
                task = Task(
                    id=str(uuid.uuid4()),
                    description=description,
                    status=get_task_status(line),
                )
                tasks.append(task)
        return tasks
