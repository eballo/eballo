import logging
import os
from pathlib import Path

from dotenv import load_dotenv

dotenv_path = Path.home() / ".config" / "taskjournal" / ".env"

if not dotenv_path.exists():
    logging.warn(f"⚠️  Warning: {dotenv_path} not found. Using default values.")

load_dotenv(dotenv_path)

# Constants loaded from .env
BASE_DIR = os.getenv("BASE_DIR", Path.home() / "Documents/DailyNotes/")
BASE_PROJECT = os.getenv(
    "BASE_PROJECT",
    Path.home() / "Documents/work/personal/eballo/taskjournal/taskjournal/",
)

# Template paths
DAILY_NOTES_TEMPLATE = os.path.join(BASE_PROJECT, "templates/dailyNotes.txt")
DAILY_NOTES_END_TEMPLATE = os.path.join(BASE_PROJECT, "templates/dailyNotes-end.txt")
WEEK_SUMMARY_TEMPLATE = os.path.join(BASE_PROJECT, "templates/weekSummary.txt")
RETRO_TEMPLATE = os.path.join(BASE_PROJECT, "templates/retro.txt")

# Jira
JIRA_ORGANIZATION = os.getenv("JIRA_ORGANIZATION", "organization")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "your-jira-key")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "<EMAIL>")
