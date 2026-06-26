# Section header keywords — single source of truth for parser and templates
SECTION_PLANNED_TASKS = "Planned Tasks"
SECTION_CODE_REVIEW_TASKS = "Code Review Tasks"
SECTION_NOTES = "Notes"
SECTION_SUMMARY = "Summary"
SECTION_FIREFIGHTER = "Firefighter"

BASE_TASKS = [
    "Check emails",
    "Check Calendar",
    "Check Jira",
    "Check Slack",
    "Check the sprint tasks in code review",
]
EXTENDED_TASKS = [
    "Check refinement tasks",
    "Get ready for the retro points",
    "Write down the summary of the week",
    "New relic alarms - report",
]

WORK_OFFICE_DAYS = ["Tuesday", "Thursday"]

NORMAL_TASKS = BASE_TASKS + EXTENDED_TASKS

# Work locations
WORK_LOCATION_HOME = "Home"
WORK_LOCATION_OFFICE = "Office"

# Placeholder sentinel values used to detect unconfigured state
PLACEHOLDER_HOME_WIFI = "CodePI"
PLACEHOLDER_OFFICE_WIFI = "TSH"
