#!/Users/eballo/Documents/work/personal/eballo/taskjournal/.venv/bin/python

import os
import argparse
import logging
from datetime import datetime

from config import BASE_DIR, DAILY_NOTES_TEMPLATE, WEEK_SUMMARY_TEMPLATE, RETRO_TEMPLATE, DAILY_NOTES_END_TEMPLATE
from services.file import get_week_folder
from services.time import calculate_working_hours
from commands import create_daily_notes_file, finalize_daily_notes, \
    create_retro_file, create_week_summary
from services.logger import logger

def main():

    parser = argparse.ArgumentParser(description="Daily Task Tracker Command Line Tool")
    parser.add_argument("command", choices=["daily-start", "daily-finish", "retro", "week-summary", "time"], help="Command to execute.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode for additional logging.", default=False)
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    today = datetime.now()
    week_folder = get_week_folder(BASE_DIR, today)

    # Ensure the directory exists
    os.makedirs(week_folder, exist_ok=True)

    if args.debug:
        logger.debug("Debug mode enabled.")
        logger.debug(f"Command: {args.command}")
        logger.debug(f"BASE_DIR: {BASE_DIR}")
        logger.debug("[Templates]")
        logger.debug(f"DAILY_NOTES_TEMPLATE: {DAILY_NOTES_TEMPLATE}")
        logger.debug(f"DAILY_NOTES_END_TEMPLATE: {DAILY_NOTES_END_TEMPLATE}")
        logger.debug(f"WEEK_SUMMARY_TEMPLATE: {WEEK_SUMMARY_TEMPLATE}")
        logger.debug(f"RETRO_TEMPLATE: {RETRO_TEMPLATE}")

    daily_notes_file = os.path.join(week_folder, f"{today.strftime('%Y-%m-%d')}-DailyNotes.txt")

    if args.command == "daily-start":
        if not os.path.exists(daily_notes_file):
            estimated_time = create_daily_notes_file(daily_notes_file, DAILY_NOTES_TEMPLATE)
            logger.info(f"Daily notes file created: {daily_notes_file}")
            logger.info(f"Estimated finish time: {estimated_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            logger.warning(f"Daily notes file already exists: {daily_notes_file}")

    elif args.command == "daily-finish":
        if os.path.exists(daily_notes_file):
            finalize_daily_notes(daily_notes_file)
            logger.info(f"Daily notes finalized: {daily_notes_file}")
        else:
            logger.warning(f"Daily notes file does not exist: {daily_notes_file}")

    elif args.command == "retro":
        retro_file = create_retro_file(week_folder, RETRO_TEMPLATE)
        logger.info(f"Retro file ensured: {retro_file}")

    elif args.command == "week-summary":
        create_week_summary(week_folder, WEEK_SUMMARY_TEMPLATE)
        logger.info(f"Week summary file ensured: {os.path.join(week_folder, 'week-summary.txt')}")

    elif args.command == "time":
        if os.path.exists(daily_notes_file):
            started_time, elapsed_hours, finish_time = calculate_working_hours(daily_notes_file)
            if elapsed_hours is not None:
                logger.info(f"Started time: {started_time}")
                logger.info(f"Elapsed working time: {elapsed_hours:.2f}")
                logger.info(f"Estimated finish time: {finish_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                logger.error("Could not calculate working hours.")
        else:
            logger.warning(f"Daily notes file does not exist: {daily_notes_file}")

if __name__ == "__main__":
    main()
