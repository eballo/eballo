from abc import ABC, abstractmethod

from taskjournal.config import TEMPLATE_FORMAT
from taskjournal.models.task import Task, Status
from taskjournal.services.logger import logger

_STATUS_CHECKBOX: dict[Status, str] = {
    Status.DONE: "[x]",
    Status.BLOCKED: "[-]",
    Status.IN_PROGRESS: "[>]",
}


class TaskFormatStrategy(ABC):

    @property
    @abstractmethod
    def prefix(self) -> str:
        """Checkbox list prefix (e.g. ' - ' for markdown, '' for plain text)."""
        ...

    @property
    def is_txt(self) -> bool:
        return False

    @abstractmethod
    def format_task(
        self,
        task: Task,
        with_name: bool = False,
        with_status: bool = False,
    ) -> str: ...


class MarkdownFormatStrategy(TaskFormatStrategy):

    @property
    def prefix(self) -> str:
        return " - "

    def format_task(
        self,
        task: Task,
        with_name: bool = False,
        with_status: bool = False,
    ) -> str:
        checkbox = self.prefix + _STATUS_CHECKBOX.get(task.status, "[ ]")
        name = f" - {task.assignee}" if with_name and task.assignee else ""
        status = f" ({task.status.value})" if with_status and task.status else ""

        key = f"[{task.key}]" if task.key else ""
        link = f"({task.link})" if task.link else ""
        github = f"[🐙]({task.github})" if task.github else ""
        return f"{checkbox} {key}{link}{github}{task.description}{name}{status}"


class PlainTextFormatStrategy(TaskFormatStrategy):

    @property
    def prefix(self) -> str:
        return ""

    @property
    def is_txt(self) -> bool:
        return True

    def format_task(
        self,
        task: Task,
        with_name: bool = False,
        with_status: bool = False,
    ) -> str:
        checkbox = self.prefix + _STATUS_CHECKBOX.get(task.status, "[ ]")
        name = f" - {task.assignee}" if with_name and task.assignee else ""
        status = f" ({task.status.value})" if with_status and task.status else ""

        # Plain-text notes can't render markdown links, so the key stays a bare
        # tag and the URLs move to the end behind unique sentinels the parser
        # reads back (see DailyParserService._extract_txt_metadata).
        key = f"[{task.key}] " if task.key else ""
        link = f" 🔗 {task.link}" if task.link else ""
        github = f" 🐙 {task.github}" if task.github else ""
        return f"{checkbox} {key}{task.description}{name}{status}{link}{github}"


def get_format_strategy(template_format: str = TEMPLATE_FORMAT) -> TaskFormatStrategy:
    if template_format == "txt":
        return PlainTextFormatStrategy()
    return MarkdownFormatStrategy()


class TaskFormatter:

    def __init__(
        self,
        strategy: TaskFormatStrategy | None = None,
        template_format: str = TEMPLATE_FORMAT,
    ) -> None:
        if strategy is not None:
            self.strategy = strategy
        else:
            self.strategy = get_format_strategy(template_format)

    @property
    def is_txt(self) -> bool:
        return self.strategy.is_txt

    @property
    def prefix(self) -> str:
        return self.strategy.prefix

    @staticmethod
    def status_checkbox_char(status: Status) -> str:
        return _STATUS_CHECKBOX.get(status, "[ ]")[1]

    def format_task(
        self,
        task: Task,
        with_name: bool = False,
        with_status: bool = False,
    ) -> str:
        return self.strategy.format_task(
            task, with_name=with_name, with_status=with_status
        )

    def format_tasks(
        self, tasks: list[Task], with_name: bool = False, with_status: bool = False
    ) -> str:
        logger.debug(tasks)
        lines = [self.format_task(task, with_name, with_status) for task in tasks]
        return "\n".join(lines)
