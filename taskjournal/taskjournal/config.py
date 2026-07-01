import logging
import os
from pathlib import Path

from dotenv import load_dotenv

dotenv_path = Path.home() / ".config" / "taskjournal" / ".env"

if not dotenv_path.exists():
    logging.warning(f"⚠️  Warning: {dotenv_path} not found. Using default values.")

load_dotenv(dotenv_path)

# Constants loaded from .env
BASE_DIR = os.getenv("BASE_DIR", Path.home() / "Documents/DailyNotes/")
_bp_env = os.getenv("BASE_PROJECT", "")
BASE_PROJECT = Path(_bp_env) if _bp_env else Path(__file__).parent
BACKUP_DIR = os.getenv("BACKUP_DIR", Path.home() / "Documents/Backup/")
# Template paths
TEMPLATE_FORMAT = os.getenv("TEMPLATE_FORMAT", "md")
TEMPLATES_DIR = f"templates/{TEMPLATE_FORMAT}"
HOLIDAYS_FILE = f"holidays/holidays.{TEMPLATE_FORMAT}"
FIREMAN_WEEKS_FILE = f"fireman/fireman_weeks.{TEMPLATE_FORMAT}"
DAILY_NOTES_TEMPLATE = os.path.join(
    BASE_PROJECT, f"{TEMPLATES_DIR}/dailyNotes.{TEMPLATE_FORMAT}"
)
WEEK_SUMMARY_TEMPLATE = os.path.join(
    BASE_PROJECT, f"{TEMPLATES_DIR}/weekSummary.{TEMPLATE_FORMAT}"
)
MONTH_REVIEW_TEMPLATE = os.path.join(
    BASE_PROJECT, f"{TEMPLATES_DIR}/month.{TEMPLATE_FORMAT}"
)
HALF_YEAR_REVIEW_TEMPLATE = os.path.join(
    BASE_PROJECT, f"{TEMPLATES_DIR}/halfYear.{TEMPLATE_FORMAT}"
)
RETRO_TEMPLATE = os.path.join(BASE_PROJECT, f"{TEMPLATES_DIR}/retro.{TEMPLATE_FORMAT}")
ONE_ON_ONE_TEMPLATE = os.path.join(
    BASE_PROJECT, f"{TEMPLATES_DIR}/1on1.{TEMPLATE_FORMAT}"
)
HOLIDAYS_TEMPLATE = os.path.join(
    BASE_PROJECT, f"{TEMPLATES_DIR}/holidays.{TEMPLATE_FORMAT}"
)
FIREMAN_WEEKS_TEMPLATE = os.path.join(
    BASE_PROJECT, f"{TEMPLATES_DIR}/fireman_weeks.{TEMPLATE_FORMAT}"
)

# Jira
JIRA_ORGANIZATION = os.getenv("JIRA_ORGANIZATION", "organization")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "your-jira-key")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "<EMAIL>")
JIRA_BOARD_ID = os.getenv("JIRA_BOARD_ID", "your-jira-board-id")

# github
GIT_HUB_ORGANIZATION_NAME = os.getenv(
    "GIT_HUB_ORGANIZATION_NAME", "your-github-organization"
)
GIT_HUB_TOKEN = os.getenv("GIT_HUB_TOKEN", "your-github-token")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
AI_PROVIDER = os.getenv("AI_PROVIDER", "claude_code")

MANAGER_NAME = os.getenv("MANAGER_NAME", "")

# Wifi
HOME_WIFI = os.getenv("HOME_WIFI", "CodePI")
OFFICE_WIFI = os.getenv("OFFICE_WIFI", "TSH")

# Editor
EDITOR_APP = os.getenv("EDITOR_APP", "Obsidian")
