from taskjournal.models.task import Task, Status


class FileWriter:

    @staticmethod
    def format_task(task: Task) -> str:
        checkbox = "[ ]"
        if task.status == Status.DONE:
            checkbox = "[x]"
        elif task.status == Status.BLOCKED:
            checkbox = "[-]"

        key = f" [{task.key}] " if task.key else " "
        status = f" ({task.status.value})" if task.key else ""
        return f"{checkbox}{key}{task.description}{status}"

    @staticmethod
    def format_content(replace_content: str, content: str, tasks: list[Task]) -> str:
        lines = [FileWriter.format_task(task) for task in tasks]
        return content.replace(replace_content, "\n".join(lines))
