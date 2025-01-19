import os

import pytest
from datetime import datetime
from unittest.mock import patch, mock_open

from utils import get_week_folder, write_file, create_daily_notes_file, finalize_daily_notes, create_week_summary, \
    create_retro_file


@pytest.fixture
def mock_datetime_now():
    return datetime(2025, 1, 19, 10, 0, 0)

@pytest.fixture
def base_dir(tmp_path):
    return str(tmp_path)

@pytest.fixture
def week_folder(base_dir, mock_datetime_now):
    return get_week_folder(base_dir, mock_datetime_now)

@patch("utils.datetime")
def test_get_week_folder(mock_datetime, base_dir):
    mock_datetime.now.return_value = datetime(2025, 1, 19)
    date = mock_datetime.now()
    expected_folder = os.path.join(base_dir, "2025", "week3")
    assert get_week_folder(base_dir, date) == expected_folder

@patch("builtins.open", new_callable=mock_open)
def test_write_file(mock_file):
    file_path = "test.txt"
    content = "Hello, world!"
    write_file(file_path, content)
    mock_file.assert_called_once_with(file_path, "w")
    mock_file().write.assert_called_once_with(content)

@patch("builtins.open", new_callable=mock_open, read_data="Template with {{creation_time}} and {{tasks}}.")
@patch("utils.datetime")
def test_create_daily_notes_file(mock_datetime, mock_file):
    mock_datetime.now.return_value = datetime(2025, 1, 19, 10, 0, 0)
    file_path = "daily_notes.txt"
    template_path = "template.txt"

    create_daily_notes_file(file_path, template_path)

    mock_file.assert_any_call(template_path, "r")
    mock_file.assert_any_call(file_path, "w")

    written_content = mock_file().write.call_args[0][0]
    assert "2025-01-19 10:00:00" in written_content
    assert "[ ] Check emails" in written_content

@patch("builtins.open", new_callable=mock_open)
@patch("utils.datetime")
def test_finalize_daily_notes(mock_datetime, mock_file):
    mock_datetime.now.return_value = datetime(2025, 1, 19, 18, 0, 0)
    file_path = "daily_notes.txt"

    finalize_daily_notes(file_path)

    mock_file.assert_called_once_with(file_path, "a")
    mock_file().write.assert_called_once_with("\nFinalized: 2025-01-19 18:00:00\n")

@patch("os.path.exists", return_value=False)
@patch("os.listdir", return_value=["2025-01-18-DailyNotes.txt", "2025-01-19-DailyNotes.txt"])
@patch("builtins.open", new_callable=mock_open)
def test_create_week_summary(mock_file, mock_listdir, mock_exists, base_dir):
    week_folder = os.path.join(base_dir, "2025", "week3")
    os.makedirs(week_folder, exist_ok=True)

    for file_name in mock_listdir.return_value:
        file_path = os.path.join(week_folder, file_name)
        with open(file_path, "w") as f:
            f.write(f"Content of {file_name}")

    create_week_summary(week_folder)

    summary_file = os.path.join(week_folder, "week-summary.txt")
    mock_file.assert_any_call(summary_file, "w")
    mock_file.assert_any_call(summary_file, "a")

    written_content = "".join(call[0][0] for call in mock_file().write.call_args_list)
    assert "2025-01-18-DailyNotes.txt" in written_content
    assert "Content of 2025-01-18-DailyNotes.txt" in written_content

@patch("os.path.exists", return_value=False)
@patch("builtins.open", new_callable=mock_open)
def test_create_retro_file(mock_file, mock_exists, week_folder):
    retro_file = create_retro_file(week_folder)

    expected_path = os.path.join(week_folder, "retro.txt")
    assert retro_file == expected_path
    mock_file.assert_called_once_with(expected_path, "w")
    mock_file().write.assert_called_once_with("==== Retro ===\n\n")
