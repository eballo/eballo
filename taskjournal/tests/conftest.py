import os
import pathlib
from datetime import datetime

from pytest import fixture

from taskjournal.services.file import get_week_folder


@fixture
def mock_setup_daily(daily_notes_path, mocker):
    mocker.patch("taskjournal.cli.main.setup", return_value=(None, daily_notes_path))


@fixture
def mock_setup_week(week_folder, mocker):
    mocker.patch("taskjournal.cli.main.setup", return_value=(week_folder, None))


@fixture
def fixture_path():
    return pathlib.Path(__file__).parent / "commands/fixtures"


@fixture(autouse=True)
def mock_config_envs(mocker):
    mocker.patch(
        "taskjournal.services.time.BASE_DIR", "/mocked/path/Documents/DailyNotes/"
    )
    mocker.patch(
        "taskjournal.cli.main.DAILY_NOTES_TEMPLATE",
        "/mocked/path/Documents/work/personal/eballo/taskjournal/taskjournal/templates/dailyNotes.txt",
    )
    mocker.patch(
        "taskjournal.cli.main.DAILY_NOTES_END_TEMPLATE",
        "/mocked/path/Documents/work/personal/eballo/taskjournal/taskjournal/templates/dailyNotes-end.txt",
    )
    mocker.patch(
        "taskjournal.cli.main.WEEK_SUMMARY_TEMPLATE",
        "/mocked/path/Documents/work/personal/eballo/taskjournal/taskjournal/templates/weekSummary.txt",
    )
    mocker.patch(
        "taskjournal.cli.main.HALF_YEAR_REVIEW_TEMPLATE",
        "/mocked/path/Documents/work/personal/eballo/taskjournal/taskjournal/templates/half-year.txt",
    )
    mocker.patch(
        "taskjournal.cli.main.RETRO_TEMPLATE",
        "/mocked/path/Documents/work/personal/eballo/taskjournal/taskjournal/templates/retro.txt",
    )


@fixture
def base_dir():
    return "/mocked/path/Documents/DailyNotes/"


@fixture
def base_project():
    return "/mocked/path/Documents/work/personal/eballo/taskjournal/taskjournal/"


@fixture
def daily_notes_path(today, week_folder):
    return os.path.join(week_folder, f"{today.strftime('%Y-%m-%d')}-DailyNotes.txt")


@fixture
def daily_notes_template(base_project):
    return os.path.join(base_project, "templates/dailyNotes.txt")


@fixture
def retro_template(base_project):
    return os.path.join(base_project, "templates/retro.txt")


@fixture
def week_summary_template(base_project):
    return os.path.join(base_project, "templates/weekSummary.txt")


@fixture
def half_year_template(base_project):
    return os.path.join(base_project, "templates/half-year.txt")


@fixture
def today():
    return datetime(2025, 1, 19)  # Use a fixed date for testing


@fixture
def week_folder(base_dir, today):
    return get_week_folder(base_dir, today)
