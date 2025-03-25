import os
import pytest
from datetime import datetime
from unittest import mock

from services.task_manager import (
    get_tasks_from_daily_notes,
    normalize_task,
    get_default_tasks,
    get_previous_tasks,
)


def test_get_tasks_from_daily_notes(mocker):
    mock_file = mocker.mock_open(
        read_data="[x] Done Task\n[ ] Pending Task\n[ ] Another Pending\n"
    )
    mocker.patch("builtins.open", mock_file)

    done, pending = get_tasks_from_daily_notes("fake_path.txt")

    assert done == ["Done Task"]
    assert pending == ["Pending Task", "Another Pending"]


def test_get_tasks_from_daily_notes_error(mocker):
    mocker.patch("builtins.open", side_effect=OSError("boom"))
    mock_logger = mocker.patch("services.task_manager.logger")

    done, pending = get_tasks_from_daily_notes("badfile.txt")

    assert done == []
    assert pending == []
    mock_logger.error.assert_called_once()
    assert "boom" in mock_logger.error.call_args[0][0]


@pytest.mark.parametrize(
    "task,expected",
    [
        ("[x] Complete task", "Complete task"),
        ("[ ] Pending task", "Pending task"),
        ("No checkbox task", "No checkbox task"),
    ],
)
def test_normalize_task(task, expected):
    assert normalize_task(task) == expected


@pytest.mark.parametrize(
    "weekday,isoweek,expected_task",
    [
        ("Wednesday", 3, "[ ] Check refinement tasks"),
        ("Thursday", 4, "[ ] Get ready for the retro points"),  # even week
        ("Thursday", 3, None),  # odd week
        ("Friday", 3, "[ ] Write down the summary of the week"),
        ("Monday", 3, None),
    ],
)
def test_get_default_tasks_varies_by_day(mocker, weekday, isoweek, expected_task):
    mock_datetime = mocker.patch("services.task_manager.datetime")
    mock_datetime.now.return_value.strftime.return_value = weekday
    mock_datetime.now.return_value.isocalendar.return_value = (2025, isoweek, 1)

    tasks = get_default_tasks()

    # common tasks
    assert "[ ] Check emails" in tasks
    assert "[ ] Check Calendar" in tasks
    assert "[ ] PR reviews" in tasks

    if expected_task:
        assert expected_task in tasks
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
    result = get_previous_tasks("fake_folder", "current.txt")
    assert result == []


def test_get_previous_tasks_no_txt_files(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.listdir", return_value=["current.txt", "image.png"])
    result = get_previous_tasks("some_folder", "current.txt")
    assert result == []


def test_get_previous_tasks_success(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch(
        "os.listdir", return_value=["2025-01-18-DailyNotes.txt", "current.txt"]
    )

    mock_file = mocker.mock_open(read_data="[ ] Task 1\n[x] Task 2\n[ ] Task 3\n")
    mocker.patch("builtins.open", mock_file)

    result = get_previous_tasks("folder", "current.txt")

    assert result == ["[ ] Task 1", "[ ] Task 3"]


def test_get_previous_tasks_file_read_error(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch(
        "os.listdir", return_value=["2025-01-18-DailyNotes.txt", "current.txt"]
    )
    mocker.patch("builtins.open", side_effect=OSError("read fail"))
    mock_logger = mocker.patch("services.task_manager.logger")

    result = get_previous_tasks("folder", "current.txt")

    assert result == []
    mock_logger.warning.assert_called_once()
    assert "read fail" in mock_logger.warning.call_args[0][0]
