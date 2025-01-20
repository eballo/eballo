import os
from dotenv import load_dotenv

current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
dotenv_path = os.path.join(current_dir, ".env")

load_dotenv(dotenv_path)

# Constants loaded from .env
BASE_DIR = os.getenv("BASE_DIR", "/Users/eballo/work/DailyNotes/")
BASE_PROJECT = os.getenv("BASE_PROJECT", "/Users/eballo/work/eballo/taskjournal/taskjournal/")

# Template paths
DAILY_NOTES_TEMPLATE = os.path.join(BASE_PROJECT, "templates/dailyNotes.txt")
WEEK_SUMMARY_TEMPLATE = os.path.join(BASE_PROJECT, "templates/weekSummary.txt")
RETRO_TEMPLATE = os.path.join(BASE_PROJECT, "templates/retro.txt")