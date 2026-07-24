# Section header keywords — single source of truth for parser and templates
SECTION_PLANNED_TASKS = "Planned Tasks"
SECTION_CODE_REVIEW_TASKS = "Code Review Tasks"
SECTION_NOTES = "Notes"
SECTION_SUMMARY = "Summary"
SECTION_FIREFIGHTER = "Firefighter"

WORK_OFFICE_DAYS = ["Tuesday", "Thursday"]

# Expected working hours per weekday — Mon-Thu run longer, Friday is shorter,
# totalling the same 40h/week.
WORKDAY_HOURS_MON_TO_THU = 8.5
WORKDAY_HOURS_FRIDAY = 6.0

# Break/lunch hours per weekday — no break on Friday since the workday is already short.
WORKDAY_BREAK_HOURS_MON_TO_THU = 1.0
WORKDAY_BREAK_HOURS_FRIDAY = 0.0

# Work-hour equivalent credited for a vacation/holiday day (neutral in the weekly balance).
WORKDAY_HOURS_IF_HOLIDAY = 8.0

# Work locations
WORK_LOCATION_HOME = "Home"
WORK_LOCATION_OFFICE = "Office"

# Placeholder sentinel values used to detect unconfigured state
PLACEHOLDER_HOME_WIFI = "CodePI"
PLACEHOLDER_OFFICE_WIFI = "TSH"

# Jira query modes used by wk services jira
JIRA_MODE_DEFAULT = ""
JIRA_MODE_ALL = "all"
JIRA_MODE_MINE = "mine"
JIRA_MODE_CODE = "code"
JIRA_MODE_MIDREVIEW = "midreview"
JIRA_MODE_MONTH = "month"
