from pathlib import Path

from freezegun import freeze_time
import os
import subprocess
import sys
import argparse
from pytest import raises
from taskjournal.main import main


def test_main_daily_start(base_dir, daily_notes_template, week_folder, today, mocker):
    # Given
    mock_makedirs = mocker.patch("os.makedirs")
    mocker.patch("os.path.exists", return_value=False)
    mock_create_file = mocker.patch("taskjournal.main.create_daily_notes_file")
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(command="daily-start", debug=False),
    )

    mock_datetime = mocker.patch("taskjournal.main.datetime")
    mock_datetime.now.return_value = today

    # When
    main()

    # Then
    mock_makedirs.assert_called_once_with(week_folder, exist_ok=True)
    mock_create_file.assert_called_once_with(
        os.path.join(week_folder, f"{today.strftime('%Y-%m-%d')}-DailyNotes.txt"),
        daily_notes_template,
    )


def test_main_daily_start_file_exists(mocker, week_folder, today):
    # Given
    mocker.patch("os.path.exists", return_value=True)
    mock_warn = mocker.patch("taskjournal.main.logger.warning")
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(command="daily-start", debug=False),
    )
    mock_datetime = mocker.patch("taskjournal.main.datetime")
    mock_datetime.now.return_value = today

    # When
    main()

    # Then
    mock_warn.assert_called_once_with(
        f"Daily notes file already exists: {os.path.join(week_folder, f'{today.strftime('%Y-%m-%d')}-DailyNotes.txt')}"
    )


def test_main_daily_finish(mocker, week_folder, today):
    # Given
    daily_notes_file = os.path.join(
        week_folder, f"{today.strftime('%Y-%m-%d')}-DailyNotes.txt"
    )
    mocker.patch("os.path.exists", return_value=True)
    mock_finalize_notes = mocker.patch("taskjournal.main.finalize_daily_notes")
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(command="daily-finish", debug=False),
    )

    mock_datetime = mocker.patch("taskjournal.main.datetime")
    mock_datetime.now.return_value = today

    # When
    main()

    # Then
    mock_finalize_notes.assert_called_once_with(daily_notes_file)


def test_main_daily_finish_file_not_exist(mocker, week_folder, today):
    # Given
    mocker.patch("os.path.exists", return_value=False)
    mock_warn = mocker.patch("taskjournal.main.logger.warning")
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(command="daily-finish", debug=False),
    )
    mock_datetime = mocker.patch("taskjournal.main.datetime")
    mock_datetime.now.return_value = today

    # When
    main()

    # Then
    mock_warn.assert_called_once_with(
        f"Daily notes file does not exist: {os.path.join(week_folder, f'{today.strftime('%Y-%m-%d')}-DailyNotes.txt')}"
    )


def test_main_time_file_exists_valid(mocker, week_folder, today):
    # Given
    mocker.patch("os.path.exists", return_value=True)
    mock_logger = mocker.patch("taskjournal.main.logger")
    mock_calculate = mocker.patch("taskjournal.main.calculate_working_hours")
    mock_calculate.return_value = ("09:00", 5.5, today.replace(hour=14, minute=30))

    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(command="time", debug=False),
    )
    mock_datetime = mocker.patch("taskjournal.main.datetime")
    mock_datetime.now.return_value = today

    # When
    main()

    # Then
    assert mock_calculate.called
    mock_logger.info.assert_any_call("Started time: 09:00")
    mock_logger.info.assert_any_call("Elapsed working time: 5.50")


def test_main_time_file_exists_invalid(mocker, week_folder, today):
    # Given
    mocker.patch("os.path.exists", return_value=True)
    mock_logger = mocker.patch("taskjournal.main.logger")
    mock_calculate = mocker.patch("taskjournal.main.calculate_working_hours")
    mock_calculate.return_value = ("09:00", None, None)

    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(command="time", debug=False),
    )
    mock_datetime = mocker.patch("taskjournal.main.datetime")
    mock_datetime.now.return_value = today

    # When
    main()

    # Then
    mock_logger.error.assert_called_once_with("Could not calculate working hours.")


def test_main_time_file_not_exists(mocker, week_folder, today):
    # Given
    mocker.patch("os.path.exists", return_value=False)
    mock_logger = mocker.patch("taskjournal.main.logger")

    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(command="time", debug=False),
    )
    mock_datetime = mocker.patch("taskjournal.main.datetime")
    mock_datetime.now.return_value = today

    # When
    main()

    # Then
    mock_logger.warning.assert_called_once_with(
        f"Daily notes file does not exist: {os.path.join(week_folder, f'{today.strftime('%Y-%m-%d')}-DailyNotes.txt')}"
    )


@freeze_time("2025-01-19 10:00:00")
def test_main_retro(mocker, week_folder, retro_template):
    # Given
    mock_create_retro = mocker.patch(
        "taskjournal.main.create_retro_file",
        return_value=os.path.join(week_folder, "retro.txt"),
    )
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(command="retro", debug=False),
    )

    # When
    main()

    # Then
    mock_create_retro.assert_called_once_with(week_folder, retro_template)


@freeze_time("2025-01-19 10:00:00")
def test_main_week_summary(mocker, week_folder, week_summary_template):
    # Given
    mock_create_summary = mocker.patch("taskjournal.main.create_week_summary")
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(command="week-summary", debug=False),
    )

    # When
    main()

    # Then
    mock_create_summary.assert_called_once_with(week_folder, week_summary_template)


def test_main_debug_logging(mocker, week_folder, today):
    # Given
    mock_logger = mocker.patch("taskjournal.main.logger")
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("taskjournal.main.create_daily_notes_file")

    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(command="daily-start", debug=True),
    )
    mock_datetime = mocker.patch("taskjournal.main.datetime")
    mock_datetime.now.return_value = today

    # When
    main()

    # Then
    assert mock_logger.debug.call_count > 0


def test_main_help_output(capsys, mocker):
    # Given: simulate passing `--help` from the command line
    mocker.patch("sys.argv", ["taskjournal", "--help"])

    # When / Then
    with raises(SystemExit) as excinfo:
        main()

    # Help command should exit with code 0
    assert excinfo.value.code == 0

    # Capture output
    captured = capsys.readouterr()
    assert "Daily Task Tracker Command Line Tool" in captured.out
    assert "usage:" in captured.out
    assert "daily-start" in captured.out
    assert "daily-finish" in captured.out
    assert "retro" in captured.out
    assert "week-summary" in captured.out


def test_main_entrypoint():
    project_root = Path(__file__).resolve().parents[1]
    main_py = project_root / "taskjournal" / "main.py"

    # Run with --help
    result = subprocess.run(
        [sys.executable, str(main_py), "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # It should exit cleanly
    assert result.returncode == 0

    # The help text should appear in stdout
    assert "Daily Task Tracker Command Line Tool" in result.stdout
    assert "usage:" in result.stdout


def test_main_invalid_command_shows_help():
    project_root = Path(__file__).resolve().parents[1]
    main_py = project_root / "taskjournal" / "main.py"

    # Pass an invalid command (not in choices)
    result = subprocess.run(
        [sys.executable, str(main_py), "invalid-command"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # argparse will exit with error code 2
    assert result.returncode == 2

    # stderr should contain the error and usage/help text
    assert "invalid choice" in result.stderr
    assert "usage:" in result.stderr
