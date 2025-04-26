import pytest

from taskjournal.models.task import Status
from taskjournal.services.task_manager import (
    get_tasks_from_daily_notes,
    get_default_tasks,
    get_previous_pending_tasks,
)


def test_get_tasks_from_daily_notes(mocker):
    mock_file = mocker.mock_open(
        read_data="[x] Done Task\n[ ] Pending Task\n[ ] Another Pending\n"
    )
    mocker.patch("builtins.open", mock_file)

    tasks = get_tasks_from_daily_notes("fake_path.txt")

    assert len(tasks) == 3
    assert tasks[0].description == "Done Task"
    assert tasks[0].status == Status.DONE
    assert tasks[1].description == "Pending Task"
    assert tasks[1].status == Status.NOT_FINISHED
    assert tasks[2].description == "Another Pending"
    assert tasks[2].status == Status.NOT_FINISHED


def test_get_tasks_from_daily_notes_error(mocker):
    mocker.patch("builtins.open", side_effect=OSError("boom"))
    mock_logger = mocker.patch("taskjournal.services.task_manager.logger")

    tasks = get_tasks_from_daily_notes("badfile.txt")

    assert tasks == []
    mock_logger.error.assert_called_once()
    assert "boom" in mock_logger.error.call_args[0][0]


@pytest.mark.parametrize(
    "weekday,isoweek,expected_task, expected_len",
    [
        ("Wednesday", 3, "Check refinement tasks", 4),
        ("Thursday", 4, "Get ready for the retro points", 4),  # even week
        ("Thursday", 3, None, 3),  # odd week
        ("Friday", 3, "Write down the summary of the week", 4),
        ("Monday", 3, None, 3),
    ],
)
def test_get_default_tasks_varies_by_day(
    mocker, weekday, isoweek, expected_task, expected_len
):
    mock_datetime = mocker.patch("taskjournal.services.task_manager.datetime")
    mock_datetime.now.return_value.strftime.return_value = weekday
    mock_datetime.now.return_value.isocalendar.return_value = (2025, isoweek, 1)

    tasks = get_default_tasks()

    # common tasks
    assert len(tasks) == expected_len
    assert "Check emails" in tasks[0].description
    assert "Check Calendar" in tasks[1].description
    assert "PR reviews" in tasks[2].description

    if expected_task:
        assert expected_task in tasks[3].description
    else:
        assert all(
            exp not in tasks
            for exp in [
                "[ ] Check refinement tasks",
                "[ ] Get ready for the retro points",
                "[ ] Write down the summary of the week",
            ]
        )


def test_get_previous_tasks_folder_not_exist(mocker):
    mocker.patch("os.path.exists", return_value=False)
    result = get_previous_pending_tasks("fake_folder", "current.txt")
    assert result == []


def test_get_previous_tasks_no_txt_files(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.listdir", return_value=["current.txt", "image.png"])
    result = get_previous_pending_tasks("some_folder", "current.txt")
    assert result == []


def test_get_previous_tasks_success(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch(
        "os.listdir", return_value=["2025-01-18-DailyNotes.txt", "current.txt"]
    )

    mock_file = mocker.mock_open(read_data="[ ] Task 1\n[x] Task 2\n[ ] Task 3\n")
    mocker.patch("builtins.open", mock_file)

    result = get_previous_pending_tasks("folder", "current.txt")

    assert len(result) == 2


def test_get_previous_tasks_file_read_error(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch(
        "os.listdir", return_value=["2025-01-18-DailyNotes.txt", "current.txt"]
    )
    mocker.patch("builtins.open", side_effect=OSError("read fail"))
    mock_logger = mocker.patch("taskjournal.services.task_manager.logger")

    result = get_previous_pending_tasks("folder", "current.txt")

    assert result == []
    mock_logger.warning.assert_called_once()
    assert "read fail" in mock_logger.warning.call_args[0][0]
