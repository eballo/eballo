#!/usr/bin/env python3

import os
import argparse
from datetime import datetime

from utils import get_week_folder, create_daily_notes_file, finalize_daily_notes, \
    create_retro_file, create_week_summary

BASE_DIR = "/Users/eballo/work/DailyNotes/"
BASE_PROJECT= "/Users/eballo/work/eballo/taskjournal/taskjournal/"

# Template paths
DAILY_NOTES_TEMPLATE = BASE_PROJECT + "templates/dailyNotes.txt"
WEEK_SUMMARY_TEMPLATE = BASE_PROJECT + "templates/weekSummary.txt"
RETRO_TEMPLATE = BASE_PROJECT + "templates/retro.txt"

def main():
    parser = argparse.ArgumentParser(description="Daily Task Tracker Command Line Tool")
    parser.add_argument("command", choices=["daily-start", "daily-finish", "retro", "week-summary"], help="Command to execute.")
    args = parser.parse_args()

    today = datetime.now()
    week_folder = get_week_folder(BASE_DIR, today)

    # Ensure the directory exists
    os.makedirs(week_folder, exist_ok=True)

    # File paths
    daily_notes_file = os.path.join(week_folder, f"{today.strftime('%Y-%m-%d')}-DailyNotes.txt")

    if args.command == "daily-start":
        if not os.path.exists(daily_notes_file):
            create_daily_notes_file(daily_notes_file, DAILY_NOTES_TEMPLATE)
            print(f"Daily notes file created: {daily_notes_file}")
        else:
            print(f"Daily notes file already exists: {daily_notes_file}")

    elif args.command == "daily-finish":
        if os.path.exists(daily_notes_file):
            finalize_daily_notes(daily_notes_file)
            print(f"Daily notes finalized with timestamp: {daily_notes_file}")
        else:
            print(f"Daily notes file does not exist: {daily_notes_file}")

    elif args.command == "retro":
        retro_file = create_retro_file(week_folder, RETRO_TEMPLATE)
        print(f"Retro file ensured: {retro_file}")

    elif args.command == "week-summary":
        create_week_summary(week_folder, WEEK_SUMMARY_TEMPLATE)
        print(f"Week summary file ensured: {os.path.join(week_folder, 'week-summary.txt')}")

if __name__ == "__main__":
    main()
