import subprocess
import sys
from datetime import datetime
from pathlib import Path

from freezegun import freeze_time
from typer.testing import CliRunner

from taskjournal.cli.main import app

runner = CliRunner()


# ---------------------------------------
# Daily Start command tests
# ---------------------------------------


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_happy_path(
    mock_setup_daily, daily_notes_path, daily_notes_template, mocker
):
    # Given
    mock_create = mocker.patch("taskjournal.cli.main.create_daily_notes_file")
    # when
    result = runner.invoke(app, ["daily-start"])
    # then
    assert result.exit_code == 0
    mock_create.assert_called_once_with(
        daily_notes_path, daily_notes_template, datetime.now()
    )


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_specific_date(mock_setup_daily, daily_notes_template, mocker):
    # Given
    mock_daily_notes = "/mocked/path/Documents/work/personal/eballo/taskjournal/taskjournal/templates/dailyNotes.txt"
    mock_create = mocker.patch("taskjournal.cli.main.create_daily_notes_file")
    mock_get_week_folder_and_daily_notes_file = mocker.patch(
        "taskjournal.cli.main.get_week_folder_and_daily_notes_file",
        return_value=(
            mock_daily_notes,
            None,
        ),
    )
    # when
    result = runner.invoke(app, ["daily-start", "--date", "2025-01-25 10:00"])
    # then
    assert result.exit_code == 0
    mock_get_week_folder_and_daily_notes_file.assert_called_once()
    mock_create.assert_called_once_with(
        mock_daily_notes, daily_notes_template, datetime(2025, 1, 25, 10, 00)
    )


def test_daily_start_specific_date_invalid(
    mock_setup_daily, daily_notes_template, mocker, caplog
):
    # Given
    mock_create = mocker.patch("taskjournal.cli.main.create_daily_notes_file")
    # when
    result = runner.invoke(app, ["daily-start", "--date", "some-invalid-date"])
    # then
    assert result.exit_code == 1
    assert "❌ Invalid date format. Use 'YYYY-MM-DD HH:MM'." in caplog.text
    mock_create.assert_not_called()


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_force(
    mock_setup_daily, daily_notes_path, daily_notes_template, mocker, caplog
):
    # Given
    mock_create = mocker.patch("taskjournal.cli.main.create_daily_notes_file")
    # when
    result = runner.invoke(app, ["daily-start", "--force"])
    # then
    assert (
        "Force option is enabled. Existing daily notes file will be overwritten."
        in caplog.text
    )
    assert result.exit_code == 0
    mock_create.assert_called_once_with(
        daily_notes_path, daily_notes_template, datetime.now()
    )


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_specific_date_force(
    mock_setup_daily, daily_notes_template, mocker, caplog
):
    # Given
    mock_daily_notes = "/mocked/path/Documents/work/personal/eballo/taskjournal/taskjournal/templates/dailyNotes.txt"
    mock_create = mocker.patch("taskjournal.cli.main.create_daily_notes_file")
    mock_get_week_folder_and_daily_notes_file = mocker.patch(
        "taskjournal.cli.main.get_week_folder_and_daily_notes_file",
        return_value=(
            mock_daily_notes,
            None,
        ),
    )
    # when
    result = runner.invoke(
        app, ["daily-start", "--date", "2025-01-25 10:00", "--force"]
    )
    # then
    assert (
        "Force option is enabled. Existing daily notes file will be overwritten."
        in caplog.text
    )
    assert result.exit_code == 0
    mock_get_week_folder_and_daily_notes_file.assert_called_once()
    mock_create.assert_called_once_with(
        mock_daily_notes, daily_notes_template, datetime(2025, 1, 25, 10, 00)
    )


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_file_already_exists(
    mock_setup_daily, daily_notes_path, mocker, caplog
):
    # given
    mocker.patch("os.path.exists", return_value=True)
    # when
    result = runner.invoke(app, ["daily-start"])
    # then
    assert result.exit_code == 0
    assert "Daily notes file already exists:" in caplog.text


# ---------------------------------------
# Daily finish command tests
# ---------------------------------------


@freeze_time("2025-01-19 10:00:00")
def test_daily_finish_happy_path(mock_setup_daily, daily_notes_path, mocker, caplog):
    # given
    mocker.patch("os.path.exists", return_value=True)
    mock_finalize = mocker.patch("taskjournal.cli.main.finalize_daily_notes")
    # when
    result = runner.invoke(app, ["daily-finish"])
    # then
    assert result.exit_code == 0
    mock_finalize.assert_called_once_with(daily_notes_path, None)
    assert "Daily notes finalized" in caplog.text


@freeze_time("2025-01-19 10:00:00")
def test_daily_finish_date(mock_setup_daily, daily_notes_path, mocker, caplog):
    # given
    mock_daily_notes = "/mocked/path/Documents/work/personal/eballo/taskjournal/taskjournal/templates/dailyNotes.txt"
    mock_get_week_folder_and_daily_notes_file = mocker.patch(
        "taskjournal.cli.main.get_week_folder_and_daily_notes_file",
        return_value=(
            mock_daily_notes,
            None,
        ),
    )
    mocker.patch("os.path.exists", return_value=True)
    mock_finalize = mocker.patch("taskjournal.cli.main.finalize_daily_notes")
    # when
    result = runner.invoke(app, ["daily-finish", "--date", "2025-01-25 10:00"])
    # then
    assert result.exit_code == 0
    mock_get_week_folder_and_daily_notes_file.assert_called_once()
    mock_finalize.assert_called_once_with(
        mock_daily_notes, datetime(2025, 1, 25, 10, 00)
    )
    assert "Daily notes finalized" in caplog.text


@freeze_time("2025-01-19 10:00:00")
def test_daily_finish_date_invalid(mock_setup_daily, daily_notes_path, mocker, caplog):
    # given
    mocker.patch("os.path.exists", return_value=True)
    mock_finalize = mocker.patch("taskjournal.cli.main.finalize_daily_notes")
    # when
    result = runner.invoke(app, ["daily-finish", "--date", "some-invalid-date"])
    # then
    assert result.exit_code == 1
    mock_finalize.assert_not_called()
    assert "Invalid date format" in caplog.text


@freeze_time("2025-01-19 10:00:00")
def test_daily_finish_file_do_not_exist(mock_setup_daily, daily_notes_path, mocker):
    # given
    mocker.patch("os.path.exists", return_value=False)
    mock_warn = mocker.patch("taskjournal.cli.main.logger.warning")
    # when
    result = runner.invoke(app, ["daily-finish"])
    # then
    assert result.exit_code == 0
    mock_warn.assert_called_once_with(
        f"Daily notes file does not exist: {daily_notes_path}"
    )


# ---------------------------------------
# Daily retro command tests
# ---------------------------------------


def test_retro_command(mock_setup_week, week_folder, retro_template, mocker, caplog):
    # given
    mock_create = mocker.patch(
        "taskjournal.cli.main.create_retro_file", return_value="retro.txt"
    )
    # when
    result = runner.invoke(app, ["retro"])
    # then
    assert result.exit_code == 0
    assert "Retro file ensured" in caplog.text
    mock_create.assert_called_once_with(week_folder, retro_template)


# ---------------------------------------
# Daily week-summary command tests
# ---------------------------------------


def test_week_summary_command(
    mock_setup_week, week_folder, week_summary_template, mocker, caplog
):
    # given
    mock_create = mocker.patch("taskjournal.cli.main.create_week_summary")
    # when
    result = runner.invoke(app, ["week-summary"])
    # then
    assert result.exit_code == 0
    assert "Week summary file created at" in caplog.text
    mock_create.assert_called_once_with(week_folder, week_summary_template)


# ---------------------------------------
# Daily half-year-review command tests
# ---------------------------------------


def test_half_year_review_command(
    mock_setup_week, week_folder, half_year_template, mocker, caplog
):
    # given
    mock_create = mocker.patch("taskjournal.cli.main.create_half_year_review")
    # when
    result = runner.invoke(app, ["half-year-review"])
    # then
    assert result.exit_code == 0
    assert "Half year review file created" in caplog.text
    mock_create.assert_called_once_with(week_folder, half_year_template)


def test_time_valid(mock_setup_daily, daily_notes_path, today, mocker):
    # given
    mocker.patch("os.path.exists", return_value=True)
    mock_get_lines = mocker.patch("taskjournal.commands.commands.get_lines")
    mock_get_lines.return_value = [
        f"Created: {today.strftime('%Y-%m-%d %H:%M')}\n",
        "Task 1\n",
        "Task 2\n",
    ]
    mock_logger = mocker.patch("taskjournal.commands.commands.logger")
    mock_calculate = mocker.patch(
        "taskjournal.commands.commands.calculate_working_hours"
    )
    mock_calculate.return_value = ("09:00", 5.5, today.replace(hour=14, minute=30))
    # when
    result = runner.invoke(app, ["time"])
    # then
    assert result.exit_code == 0
    mock_logger.info.assert_any_call("Started time: 09:00")
    mock_logger.info.assert_any_call("Elapsed working time: 5.50")


def test_time_invalid(mock_setup_daily, daily_notes_path, mocker):
    # given
    mocker.patch("os.path.exists", return_value=True)
    mock_logger = mocker.patch("taskjournal.commands.commands.logger")
    mock_calculate = mocker.patch(
        "taskjournal.commands.commands.calculate_working_hours"
    )
    mock_calculate.return_value = ("09:00", None, None)
    # when
    result = runner.invoke(app, ["time"])
    # then
    assert result.exit_code == 0
    mock_logger.error.assert_called_once_with("Could not calculate working hours.")


def test_time_file_not_exists(
    mock_setup_daily, daily_notes_path, mock_config_envs, mocker
):
    # given
    mocker.patch("os.path.exists", return_value=False)
    mock_logger = mocker.patch("taskjournal.cli.main.logger")
    # when
    result = runner.invoke(app, ["time"])
    # then
    assert result.exit_code == 0
    mock_logger.warning.assert_called_once_with(
        f"Daily notes file does not exist: {daily_notes_path}"
    )


# ---------------------------------------
# Daily jira command tests
# ---------------------------------------


def test_jira_all_command(
    mock_setup_week, week_folder, week_summary_template, mocker, caplog
):
    # given
    mock_jira = mocker.patch("taskjournal.cli.main.JiraService")
    mock_jira.get_current_sprint_tasks.return_value = []
    # when
    result = runner.invoke(app, ["jira", "--all"])
    # then
    assert result.exit_code == 0
    assert "All Tasks" in caplog.text
    mock_jira.assert_called_once()


def test_jira_mine_command(
    mock_setup_week, week_folder, week_summary_template, mocker, caplog
):
    # given
    mock_jira = mocker.patch("taskjournal.cli.main.JiraService")
    mock_jira.get_current_sprint_tasks_all_assigned_to_me.return_value = []
    # when
    result = runner.invoke(app, ["jira", "--mine"])
    # then
    assert result.exit_code == 0
    assert "Current Sprint Tasks ALL assigned to me" in caplog.text
    mock_jira.assert_called_once()


def test_jira_code_command(
    mock_setup_week, week_folder, week_summary_template, mocker, caplog
):
    # given
    mock_jira = mocker.patch("taskjournal.cli.main.JiraService")
    mock_jira.get_current_sprint_tasks_in_code_review.return_value = []
    # when
    result = runner.invoke(app, ["jira", "--code"])
    # then
    assert result.exit_code == 0
    assert "Current Sprint Tasks in Code Review" in caplog.text
    mock_jira.assert_called_once()


def test_jira_midreview_command(
    mock_setup_week, week_folder, week_summary_template, mocker, caplog
):
    # given
    mock_jira = mocker.patch("taskjournal.cli.main.JiraService")
    mock_jira.get_current_tasks_assigned_to_me_last_6_months.return_value = []
    # when
    result = runner.invoke(app, ["jira", "--midreview"])
    # then
    assert result.exit_code == 0
    assert "Current Tasks assigned to me in the last 6 months" in caplog.text
    mock_jira.assert_called_once()


def test_jira_default_command(
    mock_setup_week, week_folder, week_summary_template, mocker, caplog
):
    # given
    mock_jira = mocker.patch("taskjournal.cli.main.JiraService")
    mock_jira.get_current_sprint_tasks_not_done_assigned_to_me.return_value = []
    # when
    result = runner.invoke(app, ["jira"])
    # then
    assert result.exit_code == 0
    assert "Current Sprint Tasks assigned to me (not finished)" in caplog.text
    mock_jira.assert_called_once()


def test_jira_all_command_debug(
    mock_setup_week, week_folder, week_summary_template, mocker, caplog
):
    # given
    mock_jira = mocker.patch("taskjournal.cli.main.JiraService")
    mock_jira.get_current_sprint_tasks.return_value = []
    # when
    result = runner.invoke(app, ["jira", "--all", "--debug"])
    # then
    assert result.exit_code == 0
    assert "All Tasks" in caplog.text
    assert "Debug mode enabled for JIRA integration." in caplog.text
    mock_jira.assert_called_once()


def test_debug_flag_sets_logging(mocker, caplog):
    # given
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("taskjournal.cli.main.create_daily_notes_file")
    mocker.patch(
        "taskjournal.cli.main.get_week_folder_and_daily_notes_file",
        return_value=(
            "mock_daily_notes",
            None,
        ),
    )
    # when
    result = runner.invoke(app, ["daily-start", "--debug"])
    # then
    assert result.exit_code == 0
    assert "Debug mode enabled." in caplog.text


def test_version_command(caplog):
    # when
    result = runner.invoke(app, ["version"])
    # then
    assert result.exit_code == 0
    assert "Task Journal Version:" in caplog.text


def test_help_command():
    # when
    result = runner.invoke(app, ["--help"])
    # then
    assert result.exit_code == 0
    assert "Usage" in result.stdout
    assert "daily-start" in result.stdout
    assert "daily-finish" in result.stdout
    assert "week-summary" in result.stdout
    assert "retro" in result.stdout
    assert "jira" in result.stdout
    assert "half-year-review" in result.stdout


def test_invalid_command():
    # when
    result = runner.invoke(app, ["invalid-command"])
    # then
    assert result.exit_code != 0
    assert "No such command" in result.stdout


def test_main_entrypoint_as_script():
    # given
    project_root = Path(__file__).resolve().parents[2]
    main_py = project_root / "taskjournal" / "cli" / "main.py"
    # when
    result = subprocess.run(
        [sys.executable, str(main_py), "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    # then
    assert result.returncode == 0
    assert "Usage" in result.stdout
    assert "daily-start" in result.stdout
