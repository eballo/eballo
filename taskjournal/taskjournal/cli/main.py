import logging
import os
from datetime import datetime
from typing import Optional

import typer

from taskjournal.commands.commands import (
    create_daily_notes_file,
    finalize_daily_notes,
    create_retro_file,
    create_week_summary,
    calculate_time,
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
)
from taskjournal.services.file import get_week_folder
from taskjournal.services.jira import JiraService
from taskjournal.services.logger import logger

app = typer.Typer()
__version__ = "0.3.0"


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
    week_folder = get_week_folder(BASE_DIR, today)
    os.makedirs(week_folder, exist_ok=True)
    daily_notes_file = os.path.join(
        week_folder, f"{today.strftime('%Y-%m-%d')}-DailyNotes.txt"
    )

    return week_folder, daily_notes_file


@app.command()
def daily_start(debug: bool = typer.Option(False, help="Enable debug mode")):
    _, daily_notes_file = setup(debug)
    if not os.path.exists(daily_notes_file):
        estimated_time = create_daily_notes_file(daily_notes_file, DAILY_NOTES_TEMPLATE)
        logger.info(f"Daily notes file created: {daily_notes_file}")
        logger.info(
            f"Estimated finish time: {estimated_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        logger.warning(f"Daily notes file already exists: {daily_notes_file}")


@app.command()
def daily_finish(
    debug: bool = typer.Option(False, help="Enable debug mode"),
    date: Optional[str] = typer.Option(
        None, help="Override the date (format: YYYY-MM-DD)"
    ),
):
    _, daily_notes_file = setup(debug)
    custom_date = None
    if date:
        try:
            custom_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
        except ValueError:
            typer.echo("❌ Invalid date format. Use YYYY-MM-DD.")
            raise typer.Exit(code=1)

    if os.path.exists(daily_notes_file):
        finalize_daily_notes(daily_notes_file, custom_date)
        logger.info(f"Daily notes finalized: {daily_notes_file}")
    else:
        logger.warning(f"Daily notes file does not exist: {daily_notes_file}")


@app.command()
def retro(debug: bool = typer.Option(False, help="Enable debug mode")):
    week_folder, _ = setup(debug)
    retro_file = create_retro_file(week_folder, RETRO_TEMPLATE)
    logger.info(f"Retro file ensured: {retro_file}")


@app.command()
def week_summary(debug: bool = typer.Option(False, help="Enable debug mode")):
    week_folder, _ = setup(debug)
    create_week_summary(week_folder, WEEK_SUMMARY_TEMPLATE)
    logger.info(
        f"Week summary file ensured: {os.path.join(week_folder, 'week-summary.txt')}"
    )


@app.command()
def time(debug: bool = typer.Option(False, help="Enable debug mode")):
    _, daily_notes_file = setup(debug)
    if os.path.exists(daily_notes_file):
        calculate_time(daily_notes_file)
    else:
        logger.warning(f"Daily notes file does not exist: {daily_notes_file}")


@app.command()
def version():
    logger.info(f"Task Journal Version: {__version__}")


@app.command()
def jira():
    logger.info("JIRA integration")
    service = JiraService()
    issues = service.get_current_sprint_issues(77)
    logger.info("\n📝 Current Sprint Tasks:\n")
    for issue in issues:
        logger.info(
            f"- [{issue['key']}] {issue['summary']} ({issue['timespent_hours']}h, Status: {issue['status']})"
        )


if __name__ == "__main__":
    app()
