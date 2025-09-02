import os
import pathlib
from datetime import datetime

from pytest import fixture
from typer import Typer
from typer.testing import CliRunner

from taskjournal.cli.cli import create_app
from taskjournal.services.file import get_week_folder


@fixture()
def app() -> Typer:
    return create_app()


@fixture()
def runner() -> CliRunner:
    return CliRunner()


@fixture
def fixture_path():
    return pathlib.Path(__file__).parent / "commands/fixtures"


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
