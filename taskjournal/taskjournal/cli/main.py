import logging
import os
from datetime import datetime
from typing import Optional

import typer

from taskjournal.cli import version as task_journal_version
from taskjournal.commands.commands import (
    create_daily_notes_file,
    finalize_daily_notes,
    create_retro_file,
    create_week_summary,
    calculate_time,
    create_half_year_review,
)
from taskjournal.config import (
    BASE_DIR,
    DAILY_NOTES_TEMPLATE,
    WEEK_SUMMARY_TEMPLATE,
    RETRO_TEMPLATE,
    DAILY_NOTES_END_TEMPLATE,
    JIRA_ORGANIZATION,
    JIRA_API_TOKEN,
    JIRA_EMAIL,
    HALF_YEAR_REVIEW_TEMPLATE,
)
from taskjournal.services.backup import create_backup
from taskjournal.services.github import GithubService
from taskjournal.services.jira import JiraService
from taskjournal.services.logger import logger
from taskjournal.services.time import get_week_folder_and_daily_notes_file

DEBUG_MODE_HELP_MESSAGE = "Enable debug mode"

app = typer.Typer()


def setup(debug: bool):
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled.")
        logger.debug(f"BASE_DIR: {BASE_DIR}")
        logger.debug("[Templates]")
        logger.debug(f"DAILY_NOTES_TEMPLATE: {DAILY_NOTES_TEMPLATE}")
        logger.debug(f"DAILY_NOTES_END_TEMPLATE: {DAILY_NOTES_END_TEMPLATE}")
        logger.debug(f"WEEK_SUMMARY_TEMPLATE: {WEEK_SUMMARY_TEMPLATE}")
        logger.debug(f"RETRO_TEMPLATE: {RETRO_TEMPLATE}")
        logger.debug("[JIRA]")
        logger.debug(f"JIRA_ORGANIZATION: {JIRA_ORGANIZATION}")
        logger.debug(f"JIRA_API_TOKEN: {JIRA_API_TOKEN}")
        logger.debug(f"JIRA_EMAIL: {JIRA_EMAIL}")

    today = datetime.now()
    daily_notes_file, week_folder = get_week_folder_and_daily_notes_file(today)

    return week_folder, daily_notes_file


@app.command()
def daily_start(
    debug: bool = typer.Option(False, help=DEBUG_MODE_HELP_MESSAGE),
    force: bool = typer.Option(
        False, help="Force recreate the daily notes file if it exists"
    ),
    date: Optional[str] = typer.Option(
        None, help="Override the date (format: 'YYYY-MM-DD HH:MM')"
    ),
):
    _, daily_notes_file = setup(debug)
    if force:
        logger.warning(
            "Force option is enabled. Existing daily notes file will be overwritten."
        )

    if date:
        try:
            create_datetime = datetime.strptime(date, "%Y-%m-%d %H:%M")
            daily_notes_file, _ = get_week_folder_and_daily_notes_file(create_datetime)
        except ValueError:
            logger.error("❌ Invalid date format. Use 'YYYY-MM-DD HH:MM'.")
            raise typer.Exit(code=1)
    else:
        create_datetime = datetime.now()

    if not os.path.exists(daily_notes_file) or force:
        estimated_time = create_daily_notes_file(
            daily_notes_file, DAILY_NOTES_TEMPLATE, create_datetime
        )
        logger.info(f"Daily notes file created: {daily_notes_file}")
        logger.info(
            f"Estimated finish time: {estimated_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        logger.warning(f"Daily notes file already exists: {daily_notes_file}")


@app.command()
def daily_finish(
    debug: bool = typer.Option(False, help=DEBUG_MODE_HELP_MESSAGE),
    date: Optional[str] = typer.Option(
        None, help="Override the date (format: 'YYYY-MM-DD HH:MM')"
    ),
):
    _, daily_notes_file = setup(debug)
    custom_date = None
    if date:
        try:
            custom_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
            daily_notes_file, _ = get_week_folder_and_daily_notes_file(custom_date)
        except ValueError:
            logger.error("❌ Invalid date format. Use 'YYYY-MM-DD HH:MM'.")
            raise typer.Exit(code=1)

    if os.path.exists(daily_notes_file):
        finalize_daily_notes(daily_notes_file, custom_date)
        logger.info(f"Daily notes finalized: {daily_notes_file}")
    else:
        logger.warning(f"Daily notes file does not exist: {daily_notes_file}")


@app.command()
def retro(debug: bool = typer.Option(False, help=DEBUG_MODE_HELP_MESSAGE)):
    week_folder, _ = setup(debug)
    retro_file = create_retro_file(week_folder, RETRO_TEMPLATE)
    logger.info(f"Retro file ensured: {retro_file}")


@app.command()
def week_summary(debug: bool = typer.Option(False, help=DEBUG_MODE_HELP_MESSAGE)):
    week_folder, _ = setup(debug)
    create_week_summary(week_folder, WEEK_SUMMARY_TEMPLATE)
    logger.info(
        f"Week summary file ensured: {os.path.join(week_folder, 'week-summary.txt')}"
    )


@app.command()
def half_year_review(debug: bool = typer.Option(False, help=DEBUG_MODE_HELP_MESSAGE)):
    week_folder, _ = setup(debug)
    create_half_year_review(week_folder, HALF_YEAR_REVIEW_TEMPLATE)
    logger.info(
        f"Half year review file ensured: {os.path.join(week_folder, 'half-year.txt')}"
    )


@app.command()
def time(debug: bool = typer.Option(False, help=DEBUG_MODE_HELP_MESSAGE)):
    _, daily_notes_file = setup(debug)
    if os.path.exists(daily_notes_file):
        calculate_time(daily_notes_file)
    else:
        logger.warning(f"Daily notes file does not exist: {daily_notes_file}")


@app.command()
def backup():
    backup_file = create_backup()
    logger.info(f"Backup created at: {backup_file}")


@app.command()
def version():
    logger.info(f"Task Journal Version: {task_journal_version}")


@app.command()
def git():
    git_service = GithubService()
    logger.info("Git integration")
    git_service.get_org_commit_stats(since_date=datetime(2025, 1, 1))


@app.command()
def jira(
    debug: bool = typer.Option(False, help=DEBUG_MODE_HELP_MESSAGE),
    all: bool = typer.Option(False, help="Get ALL tasks of the sprint"),
    mine: bool = typer.Option(False, help="Get ALL tasks assigned to me"),
    code: bool = typer.Option(False, help="Get ALL tasks in status 'Code Review'"),
    midreview: bool = typer.Option(
        False, help="Get ALL tasks performed by me in the last 6 months"
    ),
):
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled for JIRA integration.")
        logger.debug(f"JIRA_ORGANIZATION: {JIRA_ORGANIZATION}")

    logger.info("JIRA integration")
    service = JiraService(debug)
    if all:
        logger.info("📝 All Tasks:")
        tasks = service.get_current_sprint_tasks()
    elif mine:
        logger.info("📝 Current Sprint Tasks ALL assigned to me:")
        tasks = service.get_current_sprint_tasks_all_assigned_to_me()
    elif code:
        logger.info("📝 Current Sprint Tasks in Code Review:")
        tasks = service.get_current_sprint_tasks_in_code_review()
    elif midreview:
        logger.info("📝 Current Tasks assigned to me in the last 6 months:")
        tasks = service.get_current_tasks_assigned_to_me_last_6_months()
    else:
        logger.info("📝 Current Sprint Tasks assigned to me (not finished):")
        tasks = service.get_current_sprint_tasks_not_done_assigned_to_me()

    for task in tasks:
        logger.info(task)


if __name__ == "__main__":
    app()
