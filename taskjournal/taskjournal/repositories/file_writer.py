from taskjournal.models.task import Task, Status
from taskjournal.services.file import write_to_file


class FileWriter:

    @staticmethod
    def format_task(task: Task) -> str:
        checkbox = "[ ]"
        if task.status == Status.DONE:
            checkbox = "[x]"
        elif task.status == Status.IN_PROGRESS:
            checkbox = "[-]"
        elif task.status == Status.BLOCKED:
            checkbox = "[!]"

        return f"{checkbox} {task.description}"

    @staticmethod
    def save_tasks(file_path: str, daily_notes_content: str, tasks: list[Task]) -> None:
        lines = [FileWriter.format_task(task) for task in tasks]
        daily_notes_content = daily_notes_content.replace("{{tasks}}", "\n".join(lines))
        write_to_file(file_path, daily_notes_content)
