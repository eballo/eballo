from taskjournal.models.task import Status
from taskjournal.parser.file_parser import ParseFile


def test_get_tasks():
    lines = [
        "[x] Task 1",
        "[ ] Task 2",
        "Some other text",
        "Another line",
        "[-] Task 3",
    ]
    tasks = ParseFile.get_tasks(lines)
    assert len(tasks) == 3
    assert tasks[0].description == "Task 1"
    assert tasks[0].status == Status.DONE
    assert tasks[1].description == "Task 2"
    assert tasks[1].status == Status.TODO
    assert tasks[2].description == "Task 3"
    assert tasks[2].status == Status.BLOCKED
