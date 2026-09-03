from taskjournal.config import TEMPLATE_FORMAT
from taskjournal.models.task import Task, Status
from taskjournal.services.logger import logger

_STATUS_CHECKBOX: dict[Status, str] = {
    Status.DONE: "[x]",
    Status.BLOCKED: "[-]",
    Status.IN_PROGRESS: "[>]",
}


class TaskFormatter:

    def __init__(self, template_format: str = TEMPLATE_FORMAT) -> None:
        self.is_txt = template_format == "txt"
        self.prefix = "" if self.is_txt else " - "

    @staticmethod
    def status_checkbox_char(status: Status) -> str:
        return _STATUS_CHECKBOX.get(status, "[ ]")[1]

    def format_task(
        self,
        task: Task,
        with_name: bool,
        with_status: bool,
    ) -> str:
        checkbox = self.prefix + _STATUS_CHECKBOX.get(task.status, "[ ]")
        name = f" - {task.assignee}" if with_name and task.assignee else ""
        status = f" ({task.status.value})" if with_status and task.status else ""

        # Plain-text notes can't render markdown links, so the key stays a bare
        # tag and the URLs move to the end behind unique sentinels the parser
        # reads back (see DailyParserService._extract_txt_metadata).
        if self.is_txt:
            key = f"[{task.key}] " if task.key else ""
            link = f" 🔗 {task.link}" if task.link else ""
            github = f" 🐙 {task.github}" if task.github else ""
            return f"{checkbox} {key}{task.description}{name}{status}{link}{github}"

        key = f"[{task.key}]" if task.key else ""
        link = f"({task.link})" if task.link else ""
        github = f"[🐙]({task.github})" if task.github else ""
        return f"{checkbox} {key}{link}{github}{task.description}{name}{status}"

    def format_tasks(
        self, tasks: list[Task], with_name: bool = False, with_status: bool = False
    ) -> str:
        logger.debug(tasks)
        lines = [self.format_task(task, with_name, with_status) for task in tasks]
        return "\n".join(lines)
