from taskjournal.models.task import Status
from taskjournal.parser.file_parser import ParseFile


def test_get_tasks_with_txt_format(mocker):
    # given
    mocker.patch("taskjournal.parser.file_parser.TEMPLATE_FORMAT", "txt")

    lines = [
        "[x] Task 1",
        "[ ] Task 2",
        "Some other text",
        "Another line",
        "[-] Task 3",
    ]
    # when
    tasks = ParseFile().get_tasks(lines)
    # then
    assert len(tasks) == 3
    assert tasks[0].description == "Task 1"
    assert tasks[0].status == Status.DONE
    assert tasks[1].description == "Task 2"
    assert tasks[1].status == Status.TODO
    assert tasks[2].description == "Task 3"
    assert tasks[2].status == Status.BLOCKED


def test_get_tasks_with_md_format(mocker):
    # given
    mocker.patch("taskjournal.parser.file_parser.TEMPLATE_FORMAT", "md")

    lines = [
        " - [x] Task 1",
        " - [ ] Task 2",
        "Some other text",
        "Another line",
        " - [-] Task 3",
    ]
    # when
    tasks = ParseFile().get_tasks(lines)
    # then
    assert len(tasks) == 3
    assert tasks[0].status == Status.DONE
    assert tasks[1].status == Status.TODO
    assert tasks[2].status == Status.BLOCKED


def test_get_tasks_no_valid_lines(mocker):
    # given
    mocker.patch("taskjournal.parser.file_parser.TEMPLATE_FORMAT", "txt")

    lines = [
        "Some random text",
        "Another line",
        "Yet another line",
    ]

    # when
    tasks = ParseFile().get_tasks(lines)
    # then
    assert tasks == []
