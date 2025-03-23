from freezegun import freeze_time
from pytest import fixture
from unittest.mock import patch
from datetime import datetime
import os
import argparse

from service.file import get_week_folder
from taskjournal.main import main


@patch("os.makedirs")
def test_main_daily_start(mock_makedirs, mocker, base_dir, daily_notes_template, week_folder, today):
    # Given
    mocker.patch("os.path.exists", return_value=False)
    mock_create_file = mocker.patch("taskjournal.main.create_daily_notes_file")
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=argparse.Namespace(command="daily-start", debug=False))
    mocker.patch("taskjournal.main.datetime", wraps=datetime)

    with patch("taskjournal.main.datetime") as mock_datetime:
        mock_datetime.now.return_value = today

        # When
        main()

        # Then
        mock_makedirs.assert_called_once_with(week_folder, exist_ok=True)
        mock_create_file.assert_called_once_with(
            os.path.join(week_folder, f"{today.strftime('%Y-%m-%d')}-DailyNotes.txt"),
            daily_notes_template
        )


def test_main_daily_finish(mocker, week_folder, today):
    # Given
    daily_notes_file = os.path.join(week_folder, f"{today.strftime('%Y-%m-%d')}-DailyNotes.txt")
    mocker.patch("os.path.exists", return_value=True)
    mock_finalize_notes = mocker.patch("taskjournal.main.finalize_daily_notes")
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=argparse.Namespace(command="daily-finish", debug=False))

    with patch("taskjournal.main.datetime") as mock_datetime:
        mock_datetime.now.return_value = today

        # When
        main()

        # Then
        mock_finalize_notes.assert_called_once_with(daily_notes_file)


@freeze_time("2025-01-19 10:00:00")
def test_main_retro(mocker, week_folder, retro_template):
    # Given
    mock_create_retro = mocker.patch("taskjournal.main.create_retro_file", return_value=os.path.join(week_folder, "retro.txt"))
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=argparse.Namespace(command="retro", debug=False))

    # When
    main()

    # Then
    mock_create_retro.assert_called_once_with(week_folder, retro_template)


@freeze_time("2025-01-19 10:00:00")
def test_main_week_summary(mocker, week_folder, week_summary_template):
    # Given
    mock_create_summary = mocker.patch("taskjournal.main.create_week_summary")
    mocker.patch("argparse.ArgumentParser.parse_args",
                 return_value=argparse.Namespace(command="week-summary", debug=False))


    # When
    main()

    # Then
    mock_create_summary.assert_called_once_with(week_folder, week_summary_template)


def test_get_week_folder(base_dir, today):
    # when
    week_folder = get_week_folder(base_dir, today)

    # Then
    expected_path = os.path.join(base_dir, f"{today.year}", f"week{today.isocalendar()[1]}")
    assert week_folder == expected_path

