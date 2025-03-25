from datetime import datetime, timedelta
from freezegun import freeze_time
from services.time import (
    calculate_working_hours,
    get_total_time_from_daily_notes,
    estimated_finish_time,
)


@freeze_time("2025-01-19 12:00:00")
def test_calculate_working_hours_valid(mocker):
    # Simulate a file with a start time 3 hours earlier
    created_time = "2025-01-19 09:00:00"
    mock_open = mocker.mock_open(read_data=f"Start time: {created_time}\n")
    mocker.patch("builtins.open", mock_open)

    created, elapsed, finish = calculate_working_hours("notes.txt")

    assert created == datetime.strptime(created_time, "%Y-%m-%d %H:%M:%S")
    assert round(elapsed, 1) == 3.0
    assert finish == created + timedelta(hours=9)


def test_calculate_working_hours_no_start_line(mocker):
    mock_open = mocker.mock_open(read_data="Task: something\nAnother line\n")
    mocker.patch("builtins.open", mock_open)
    mock_logger = mocker.patch("services.time.logger")

    created, elapsed, finish = calculate_working_hours("notes.txt")

    assert created is None
    assert elapsed is None
    assert finish is None
    mock_logger.warning.assert_called_once()


def test_calculate_working_hours_malformed_start(mocker):
    mock_open = mocker.mock_open(read_data="Start time: not-a-date\n")
    mocker.patch("builtins.open", mock_open)
    mock_logger = mocker.patch("services.time.logger")

    created, elapsed, finish = calculate_working_hours("notes.txt")

    assert created is None
    assert elapsed is None
    assert finish is None
    mock_logger.error.assert_called_once()


def test_calculate_working_hours_file_error(mocker):
    mocker.patch("builtins.open", side_effect=OSError("Read fail"))
    mock_logger = mocker.patch("services.time.logger")

    created, elapsed, finish = calculate_working_hours("notes.txt")

    assert created is None
    assert elapsed is None
    assert finish is None
    mock_logger.error.assert_called_once()


def test_get_total_time_from_daily_notes_single_entry(mocker):
    mock_open = mocker.mock_open(read_data="Total Time Spent: 01:15:30\n")
    mocker.patch("builtins.open", mock_open)

    total_seconds = get_total_time_from_daily_notes("file.txt")
    assert total_seconds == 1 * 3600 + 15 * 60 + 30


def test_get_total_time_from_daily_notes_multiple_entries(mocker):
    data = """Total Time Spent: 00:30:00
Task: something
Total Time Spent: 01:00:00
"""
    mock_open = mocker.mock_open(read_data=data)
    mocker.patch("builtins.open", mock_open)

    total = get_total_time_from_daily_notes("file.txt")
    assert total == 5400  # 1.5 hours


def test_get_total_time_from_daily_notes_malformed_ignored(mocker):
    data = """Total Time Spent: abc
Total Time Spent: 01:00:00"""
    mock_open = mocker.mock_open(read_data=data)
    mocker.patch("builtins.open", mock_open)

    total = get_total_time_from_daily_notes("file.txt")
    assert total == 3600


def test_estimated_finish_time():
    created = datetime(2025, 1, 19, 9, 0, 0)
    result = estimated_finish_time(created)
    assert result == created + timedelta(hours=9)
