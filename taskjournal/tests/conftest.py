import os
from datetime import datetime

from pytest import fixture

from service.file import get_week_folder


@fixture
def base_dir():
    return "/Users/eballo/Documents/DailyNotes/"

@fixture
def base_project():
    return "/Users/eballo/Documents/work/personal/eballo/taskjournal/taskjournal/"

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
def today():
    return datetime(2025, 1, 19)  # Use a fixed date for testing

@fixture
def week_folder(base_dir, today):
    return get_week_folder(base_dir, today)
