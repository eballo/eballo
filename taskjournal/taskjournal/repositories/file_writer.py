from taskjournal.models.task import Task, Status


class FileWriter:

    @staticmethod
    def format_task(task: Task, with_name: bool, with_status: bool) -> str:
        checkbox = "[ ]"
        if task.status == Status.DONE:
            checkbox = "[x]"
        elif task.status == Status.BLOCKED:
            checkbox = "[-]"

        key = f" [{task.key}] " if task.key else " "
        name = f" - {task.assignee} " if with_name and task.assignee else " "
        status = f" ({task.status.value}) " if with_status and task.status else " "
        return f"{checkbox}{key}{task.description}{name}{status}"

    @staticmethod
    def format_content(
        replace_content: str,
        content: str,
        tasks: list[Task],
        with_name: bool = False,
        with_status: bool = False,
    ) -> str:
        lines = [FileWriter.format_task(task, with_name, with_status) for task in tasks]
        return content.replace(replace_content, "\n".join(lines))
