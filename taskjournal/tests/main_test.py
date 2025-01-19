import pytest
from unittest.mock import patch
from datetime import datetime
import os
import argparse

from taskjournal.main import main
from taskjournal.utils import get_week_folder

@pytest.fixture
def base_dir():
    return "/Users/eballo/Documents/DailyNotes/"

@pytest.fixture
def base_project():
    return "/Users/eballo/Documents/work/eballo/eballo/taskjournal/taskjournal/"

@pytest.fixture
def daily_notes_template(base_project):
    return os.path.join(base_project, "templates/dailyNotes.txt")

@pytest.fixture
def today():
    return datetime(2025, 1, 19)  # Use a fixed date for testing

@pytest.fixture
def week_folder(base_dir, today):
    return get_week_folder(base_dir, today)

@patch("os.makedirs")
def test_main_daily_start(mock_makedirs, mocker, base_dir, daily_notes_template, week_folder, today):
    # Mock functions
    mocker.patch("os.path.exists", return_value=False)
    mock_create_file = mocker.patch("taskjournal.main.create_daily_notes_file")

    # Prepare command-line arguments
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=argparse.Namespace(command="daily-start"))
    mocker.patch("taskjournal.main.datetime", wraps=datetime)

    with patch("taskjournal.main.datetime") as mock_datetime:
        mock_datetime.now.return_value = today

        # Call main
        main()

        # Assertions
        mock_makedirs.assert_called_once_with(week_folder, exist_ok=True)
        mock_create_file.assert_called_once_with(
            os.path.join(week_folder, f"{today.strftime('%Y-%m-%d')}-DailyNotes.txt"),
            daily_notes_template
        )

def test_main_daily_finish(mocker, week_folder, today):
    daily_notes_file = os.path.join(week_folder, f"{today.strftime('%Y-%m-%d')}-DailyNotes.txt")

    # Mock functions
    mocker.patch("os.path.exists", return_value=True)
    mock_finalize_notes = mocker.patch("taskjournal.main.finalize_daily_notes")

    # Prepare command-line arguments
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=argparse.Namespace(command="daily-finish"))

    with patch("taskjournal.main.datetime") as mock_datetime:
        mock_datetime.now.return_value = today

        # Call main
        main()

        # Assertions
        mock_finalize_notes.assert_called_once_with(daily_notes_file)

def test_main_retro(mocker, week_folder):
    mock_create_retro = mocker.patch("taskjournal.main.create_retro_file", return_value=os.path.join(week_folder, "retro.txt"))

    # Prepare command-line arguments
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=argparse.Namespace(command="retro"))

    # Call main
    main()

    # Assertions
    mock_create_retro.assert_called_once_with(week_folder)

def test_main_week_summary(mocker, week_folder):
    mock_create_summary = mocker.patch("taskjournal.main.create_week_summary")

    # Prepare command-line arguments
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=argparse.Namespace(command="week-summary"))

    # Call main
    main()

    # Assertions
    mock_create_summary.assert_called_once_with(week_folder)


def test_get_week_folder(base_dir, today):
    week_folder = get_week_folder(base_dir, today)

    # Assert the folder path is correctly calculated
    expected_path = os.path.join(base_dir, f"{today.year}", f"week{today.isocalendar()[1]}")
    assert week_folder == expected_path

