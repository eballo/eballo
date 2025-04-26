import uuid
from typing import Literal

from taskjournal.models.task import Task, Status


def get_task_status(
    line: str,
) -> Literal[Status.DONE, Status.NOT_FINISHED, Status.BLOCKED]:
    if line.startswith("[x]"):
        return Status.DONE
    elif line.startswith("[-]"):
        return Status.BLOCKED
    else:
        return Status.NOT_FINISHED


class ParseFile:

    @staticmethod
    def get_tasks(lines: list[str]) -> list[Task]:
        tasks = []
        for line in lines:
            if line.startswith("["):
                task = Task(
                    id=str(uuid.uuid4()),
                    description=line[4:].strip(),
                    status=get_task_status(line),
                )
                tasks.append(task)
        return tasks
