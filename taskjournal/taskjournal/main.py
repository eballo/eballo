#!/Users/eballo/Documents/work/personal/eballo/taskjournal/.venv/bin/python

import os
import logging
from datetime import datetime

import typer
from taskjournal.config import (
    BASE_DIR,
    DAILY_NOTES_TEMPLATE,
    WEEK_SUMMARY_TEMPLATE,
    RETRO_TEMPLATE,
    DAILY_NOTES_END_TEMPLATE,
)
from taskjournal.services.file import get_week_folder
from taskjournal.services.time import calculate_working_hours
from taskjournal.commands import (
    create_daily_notes_file,
    finalize_daily_notes,
    create_retro_file,
    create_week_summary,
)
from taskjournal.services.logger import logger

app = typer.Typer()
__version__ = "0.1.0"


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
def daily_finish(debug: bool = typer.Option(False, help="Enable debug mode")):
    _, daily_notes_file = setup(debug)
    if os.path.exists(daily_notes_file):
        finalize_daily_notes(daily_notes_file)
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
        started_time, elapsed_hours, finish_time = calculate_working_hours(
            daily_notes_file
        )
        if elapsed_hours is not None:
            logger.info(f"Started time: {started_time}")
            logger.info(f"Elapsed working time: {elapsed_hours:.2f}")
            logger.info(
                f"Estimated finish time: {finish_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            logger.error("Could not calculate working hours.")
    else:
        logger.warning(f"Daily notes file does not exist: {daily_notes_file}")


@app.command()
def version():
    logger.info(f"Task Journal Version: {__version__}")


if __name__ == "__main__":
    app()
