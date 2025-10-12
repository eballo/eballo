from taskjournal.config import TEMPLATE_FORMAT
from taskjournal.models.task import Task, Status
from taskjournal.services.logger import logger


class TaskFormatter:

    def __init__(self):
        self.prefix = "" if TEMPLATE_FORMAT == "txt" else " - "

    # FIXME: feature #43 make TaskFormatter compatible for txt (links)
    def format_task(
        self,
        task: Task,
        with_name: bool,
        with_status: bool,
    ) -> str:
        checkbox = self.prefix + "[ ]"
        if task.status == Status.DONE:
            checkbox = self.prefix + "[x]"
        elif task.status == Status.BLOCKED:
            checkbox = self.prefix + "[-]"

        key = f" [{task.key}]" if task.key else " "
        link = f"({task.link})" if task.link else ""
        name = f" - {task.assignee}" if with_name and task.assignee else " "
        status = f" ({task.status.value})" if with_status and task.status else " "
        github = f"[🐙]({task.github})" if task.github else ""
        return f"{checkbox} {key}{link} {github} {task.description}{name}{status}"

    def format_tasks(
        self, tasks: list[Task], with_name: bool = False, with_status: bool = False
    ) -> str:
        logger.debug(tasks)
        lines = [self.format_task(task, with_name, with_status) for task in tasks]
        return "\n".join(lines)
