from taskjournal.config import TEMPLATE_FORMAT
from taskjournal.models.task import Task, Status


class FileWriter:

    def __init__(self):
        self.prefix = "" if TEMPLATE_FORMAT == "txt" else " - "

    def format_task(self, task: Task, with_name: bool, with_status: bool) -> str:
        checkbox = self.prefix + "[ ]"
        if task.status == Status.DONE:
            checkbox = self.prefix + "[x]"
        elif task.status == Status.BLOCKED:
            checkbox = self.prefix + "[-]"

        key = f" [{task.key}] " if task.key else " "
        name = f" - {task.assignee} " if with_name and task.assignee else " "
        status = f" ({task.status.value}) " if with_status and task.status else " "
        return f"{checkbox}{key}{task.description}{name}{status}"

    def format_content(
        self,
        replace_content: str,
        content: str,
        tasks: list[Task],
        with_name: bool = False,
        with_status: bool = False,
    ) -> str:
        lines = [self.format_task(task, with_name, with_status) for task in tasks]
        return content.replace(replace_content, "\n".join(lines))
