import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from freezegun import freeze_time
from typer.testing import CliRunner

from taskjournal.cli.main import app

runner = CliRunner()


@pytest.fixture
def daily_notes_path(today, week_folder):
    return os.path.join(week_folder, f"{today.strftime('%Y-%m-%d')}-DailyNotes.txt")


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_creates_file(mocker, daily_notes_path, daily_notes_template):
    mocker.patch("os.makedirs")
    mocker.patch("os.path.exists", return_value=False)
    mock_create = mocker.patch("taskjournal.cli.main.create_daily_notes_file")

    result = runner.invoke(app, ["daily-start"])

    assert result.exit_code == 0
    mock_create.assert_called_once_with(
        daily_notes_path, daily_notes_template, datetime.now()
    )


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_file_exists(mocker, daily_notes_path):
    mocker.patch("os.makedirs")
    mocker.patch("os.path.exists", return_value=True)
    mock_warn = mocker.patch("taskjournal.cli.main.logger.warning")

    result = runner.invoke(app, ["daily-start"])

    assert result.exit_code == 0
    mock_warn.assert_called_once_with(
        f"Daily notes file already exists: {daily_notes_path}"
    )


@freeze_time("2025-01-19 10:00:00")
def test_daily_finish(mocker, daily_notes_path):
    mocker.patch("os.path.exists", return_value=True)
    mock_finalize = mocker.patch("taskjournal.cli.main.finalize_daily_notes")

    result = runner.invoke(app, ["daily-finish"])

    assert result.exit_code == 0
    mock_finalize.assert_called_once_with(daily_notes_path, None)


@freeze_time("2025-01-19 10:00:00")
def test_daily_finish_file_not_exist(mocker, daily_notes_path):
    mocker.patch("os.path.exists", return_value=False)
    mock_warn = mocker.patch("taskjournal.cli.main.logger.warning")

    result = runner.invoke(app, ["daily-finish"])

    assert result.exit_code == 0
    mock_warn.assert_called_once_with(
        f"Daily notes file does not exist: {daily_notes_path}"
    )


def test_time_valid(mocker, daily_notes_path, today):
    mocker.patch("os.path.exists", return_value=True)
    mock_logger = mocker.patch("taskjournal.commands.commands.logger")
    mock_calculate = mocker.patch(
        "taskjournal.commands.commands.calculate_working_hours"
    )
    mock_calculate.return_value = ("09:00", 5.5, today.replace(hour=14, minute=30))

    result = runner.invoke(app, ["time"])

    assert result.exit_code == 0
    mock_logger.info.assert_any_call("Started time: 09:00")
    mock_logger.info.assert_any_call("Elapsed working time: 5.50")


def test_time_invalid(mocker, daily_notes_path):
    mocker.patch("os.path.exists", return_value=True)
    mock_logger = mocker.patch("taskjournal.commands.commands.logger")
    mock_calculate = mocker.patch(
        "taskjournal.commands.commands.calculate_working_hours"
    )
    mock_calculate.return_value = ("09:00", None, None)

    result = runner.invoke(app, ["time"])

    assert result.exit_code == 0
    mock_logger.error.assert_called_once_with("Could not calculate working hours.")


@freeze_time("2025-01-19 10:00:00")
def test_time_file_not_exists(mocker, daily_notes_path):
    mocker.patch("os.path.exists", return_value=False)
    mock_logger = mocker.patch("taskjournal.cli.main.logger")

    result = runner.invoke(app, ["time"])

    assert result.exit_code == 0
    mock_logger.warning.assert_called_once_with(
        f"Daily notes file does not exist: {daily_notes_path}"
    )


@freeze_time("2025-01-19 10:00:00")
def test_retro_command(mocker, week_folder, retro_template):
    mock_create = mocker.patch(
        "taskjournal.cli.main.create_retro_file", return_value="retro.txt"
    )
    result = runner.invoke(app, ["retro"])

    assert result.exit_code == 0
    mock_create.assert_called_once_with(week_folder, retro_template)


@freeze_time("2025-01-19 10:00:00")
def test_week_summary_command(mocker, week_folder, week_summary_template):
    mock_create = mocker.patch("taskjournal.cli.main.create_week_summary")

    result = runner.invoke(app, ["week-summary"])

    assert result.exit_code == 0
    mock_create.assert_called_once_with(week_folder, week_summary_template)


def test_debug_flag_sets_logging(mocker):
    mock_logger = mocker.patch("taskjournal.cli.main.logger")
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("taskjournal.cli.main.create_daily_notes_file")

    result = runner.invoke(app, ["daily-start", "--debug"])

    assert result.exit_code == 0
    assert mock_logger.debug.call_count > 0


def test_help_command():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage" in result.stdout
    assert "daily-start" in result.stdout
    assert "daily-finish" in result.stdout
    assert "week-summary" in result.stdout


def test_invalid_command():
    result = runner.invoke(app, ["invalid-command"])

    assert result.exit_code != 0
    assert "No such command" in result.stdout


def test_main_entrypoint_as_script():
    project_root = Path(__file__).resolve().parents[2]
    main_py = project_root / "taskjournal" / "cli" / "main.py"

    result = subprocess.run(
        [sys.executable, str(main_py), "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0
    assert "Usage" in result.stdout
    assert "daily-start" in result.stdout
