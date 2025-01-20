#!/Users/eballo/Documents/work/eballo/eballo/taskjournal/.venv/bin/python

import os
import argparse
from datetime import datetime

from constants import BASE_DIR, DAILY_NOTES_TEMPLATE, WEEK_SUMMARY_TEMPLATE, RETRO_TEMPLATE
from utils import get_week_folder, create_daily_notes_file, finalize_daily_notes, \
    create_retro_file, create_week_summary, calculate_working_hours


def main():

    parser = argparse.ArgumentParser(description="Daily Task Tracker Command Line Tool")
    parser.add_argument("command", choices=["daily-start", "daily-finish", "retro", "week-summary", "time"], help="Command to execute.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode for additional logging.")
    args = parser.parse_args()

    today = datetime.now()
    week_folder = get_week_folder(BASE_DIR, today)

    # Ensure the directory exists
    os.makedirs(week_folder, exist_ok=True)

    if args.debug:
        print(f"Debug mode enabled.")
        print(f"Command: {args.command}")
        print("")
        print("-------")
        print(f"BASE_DIR: {BASE_DIR}")
        print(f"DAILY_NOTES_TEMPLATE: {DAILY_NOTES_TEMPLATE}")
        print(f"WEEK_SUMMARY_TEMPLATE: {WEEK_SUMMARY_TEMPLATE}")
        print(f"RETRO_TEMPLATE: {RETRO_TEMPLATE}")
        print("----")
        print("")

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

    elif args.command == "time":
        if os.path.exists(daily_notes_file):
            started_time, elapsed_hours, finish_time = calculate_working_hours(daily_notes_file)
            if elapsed_hours is not None:
                print(f"Started time: {started_time}")
                print(f"Elapsed working hours: {elapsed_hours:.2f}")
                print(f"Estimated finish time: {finish_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print("Could not calculate working hours.")
        else:
            print(f"Daily notes file does not exist: {daily_notes_file}")

if __name__ == "__main__":
    main()
