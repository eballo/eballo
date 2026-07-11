# Task Journal

[![Version](https://img.shields.io/badge/version-0.63.0-blue.svg)](#task-journal)
[![Python](https://img.shields.io/badge/python-3.12%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/deps-uv-DE5FE9.svg?logo=astral&logoColor=white)](https://docs.astral.sh/uv/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC.svg?logo=pytest&logoColor=white)](https://docs.pytest.org/)

Task Journal (`wk`) is a Python CLI to manage your day-to-day engineering journal.

It helps you:
- create and finalize daily notes from templates
- track time spent and working days
- carry pending tasks forward between days/weeks
- generate weekly, monthly, quarterly, half-year, and yearly reports
- compare stats across months or quarters side by side
- generate AI-assisted summaries
- pull context from Jira and GitHub
- manage pull request reviews
- log professional feedback (received and given)
- compute holidays and working-day statistics
- track firefighter duty weeks
- read macOS Screen Time app usage (opt-in)
- create backups and migrate legacy files

For the full explanation of features, configuration, and command examples, see:
[Tool Overview](docs/tool-overview.md)

## Features

### Daily workflow (`wk daily`)

- `wk daily start` — create a daily note from a template, carrying pending tasks forward
- `wk daily start --date 'YYYY-MM-DD HH:MM' --force` — create for a specific date, overwriting if it exists
- `wk daily start --ff` — firefighter mode (marks the day accordingly)
- `wk daily start --w Home|Office` — specify working location (auto-detected via WiFi if configured)
- `wk daily start --offline` — skip all Jira and GitHub API calls
- `wk daily finish` — write end time and calculate total time spent
- `wk daily finish --date 'YYYY-MM-DD HH:MM'` — finalize a specific day
- `wk daily time` — show elapsed working time for today
- `wk daily status` — show elapsed time, task breakdown, and finalization state
- `wk daily check` — validate the structure and completeness of a daily note
- `wk daily sync` — pull latest Jira tasks and add any missing ones to today's note
- `wk daily audit` — scan all notes for a year and list incomplete ones
- `wk daily audit --fix` — interactively fix incomplete notes (set end time, summary)

`wk daily start` and `wk daily finish` display a brief animated marquee after completing (transient — leaves no trace in the terminal).

### Alarm management (`wk alarm`)

`wk daily start` automatically creates two macOS Reminders: a calm-down notice 30 minutes before the estimated finish, and a wrap-up notice at the estimated finish. `wk daily finish` cancels both. This feature can be toggled via `wk setup` or by setting `DAILY_ALARMS_ENABLED=false` in `.env`.

- `wk alarm list` — list tracked end-of-day alarms for the past 4 weeks (shows date, time, message, and status)
- `wk alarm set --time HH:MM [--date YYYY-MM-DD] [--message "text"]` — set or reschedule an alarm for a given date
- `wk alarm cancel [--date YYYY-MM-DD]` — cancel the alarm for a given date (defaults to today)
- `wk alarm cancel --all` — cancel every tracked alarm, including stale ones

### Task management (`wk task`)

- `wk task list` — list all tasks for today with status icons
- `wk task add <description>` — add a new planned task
- `wk task done <description>` — mark a task as done (partial match)
- `wk task wip <description>` — mark a task as work in progress
- `wk task block <description>` — mark a task as blocked
- `wk task recurring add <description>` — add a recurring task (injected automatically every day)
- `wk task recurring add <description> --every monday,wednesday` — recurring on specific weekdays
- `wk task recurring list` — list all recurring tasks
- `wk task recurring remove <description>` — remove a recurring task

All task commands accept `--date YYYY-MM-DD` to target a specific day.

### Quick capture (`wk note`, `wk standup`)

- `wk note "text"` — append a timestamped note to today's Notes section without opening the file
- `wk note "text" --date YYYY-MM-DD` — append to a specific day
- `wk standup` — show standup summary: yesterday done, done today, today planned, blockers

### Reports (`wk week`, `wk report`)

- `wk week report` — generate a weekly summary
- `wk week list` — list daily notes for a week with status and time logged
- `wk week recreate-since --date YYYY-MM-DD` — regenerate all weekly reports from a date up to today
- `wk report month` — create a monthly report
- `wk report quarter` — create a quarterly report (Q1–Q4) for the quarter containing today
- `wk report quarter --date YYYY-MM-DD` — create a quarterly report for a specific quarter
- `wk report year` — create a yearly report for the current year
- `wk report year --date YYYY-MM-DD` — create a yearly report for a specific year
- `wk report half-year` — create a half-year report
- `wk report retro` — create or open a retrospective file for the current sprint
- `wk report 1on1 create` — create a 1-on-1 meeting note
- `wk report 1on1 add-topic -t 'topic'` — append a topic to the next 1-on-1 without opening the file
- `wk report compare months` — compare monthly stats across the full year in a table
- `wk report compare months --year 2025` — compare months for a specific year
- `wk report compare quarters` — compare Q1–Q4 stats in a table
- `wk report compare quarters --year 2025` — compare quarters for a specific year

### Statistics (`wk statistics`)

- `wk statistics all --year 2026` — summary of working days for the year
- `wk statistics progress` — progress through working days so far
- `wk statistics real` — actual working days including holidays taken
- `wk statistics streak` — consecutive journaling streak and all-time record
- `wk statistics completion` — daily task completion rate over time
- `wk statistics workload` — hours worked per week, with overload warnings
- `wk statistics patterns` — productivity patterns (best day, carry-over rate, etc.)
- `wk statistics tags` — days spent per epic tag

### Calendar (`wk holidays`, `wk fireman`)

**Holidays:**
- `wk holidays all --year 2026` — list all holidays for the year
- `wk holidays upcoming` — list upcoming holidays
- `wk holidays past` — list past holidays
- `wk holidays summary` — summary of holidays (done, remaining, next)
- `wk holidays add YYYY-MM-DD 'description'` — add a holiday entry
- `wk holidays populate` — generate Markdown files from the holidays list

**Firefighter weeks:**
- `wk fireman add YYYY-MM-DD` — register a firefighter duty week (any date in the week)
- `wk fireman list` — list all registered firefighter weeks for the year
- `wk fireman upcoming` — show upcoming firefighter weeks
- `wk fireman summary` — summary of done, remaining, and next firefighter week

### Feedback (`wk feedback`)

Log professional feedback for performance reviews and half-year reports:

- `wk feedback received "text" --from "Name"` — log feedback you received
- `wk feedback received "text" --from "Name" --context "PR #42"` — with optional context
- `wk feedback given "text" --to "Name"` — log feedback you gave
- `wk feedback list` — list all feedback for the current year
- `wk feedback list --quarter 2` — filter by quarter
- `wk feedback list --from "Name"` — filter by person
- `wk feedback list --type received|given` — filter by type

All commands accept `--date YYYY-MM-DD` to set the entry date (default: today).

### Fun (`wk joke`)

- `wk joke` — fetch and display a random joke from jokeapi.dev (with a spinner between setup and punchline); falls back to a local list if offline

### Pull requests (`wk pr`)

- `wk pr list` — list open PRs waiting for your review
- `wk pr sync` — add PRs pending review as tasks in today's daily notes

### Search (`wk search`)

- `wk search -q <keyword>` — search across all notes and report files
- `wk search -q <keyword> --from YYYY-MM-DD --to YYYY-MM-DD` — filter by date range
- `wk search -q <keyword> --type daily|week` — filter by file type

### Admin (`wk setup`, `wk doctor`, `wk backup`, `wk migrate`)

- `wk setup` — interactive wizard to configure paths, Jira, GitHub, AI provider, WiFi, editor, and manager
- `wk doctor` — health check of configuration and all external integrations
- `wk info show` — show current date, week, file paths, and integration status
- `wk backup run` — create a backup of all notes
- `wk backup schedule --time HH:MM` — schedule an automatic daily backup via cron
- `wk backup schedule --disable` — remove the scheduled backup
- `wk migrate daily <path>` — migrate legacy `.txt` daily notes to `.md` format

### Service tools (`wk services`)

These commands are useful for diagnostics and standalone queries:

- `wk services jira` — query Jira tasks (flags: `--mine`, `--all`, `--code`, `--midreview`, `--month`)
- `wk services git --stats` — show GitHub commit stats for the organisation
- `wk services claude` — send a test prompt to the active AI service
- `wk services screentime` — show today's macOS Screen Time app usage (requires `SCREEN_TIME_ENABLED=true`)

## Configuration

Task Journal loads environment variables from `~/.config/taskjournal/.env`.

Create it from the sample file:

```bash
mkdir -p ~/.config/taskjournal
cp sample.env ~/.config/taskjournal/.env
```

Or run the interactive wizard:

```bash
wk setup
```

Key variables:

| Variable | Purpose |
|---|---|
| `BASE_DIR` | Root folder where daily and weekly files are stored |
| `BACKUP_DIR` | Folder for backups |
| `TEMPLATE_FORMAT` | `md` or `txt` |
| `JIRA_ORGANIZATION` | Jira subdomain (e.g. `mycompany`) |
| `JIRA_EMAIL` | Jira account email |
| `JIRA_API_TOKEN` | Jira API token |
| `JIRA_BOARD_ID` | Jira board ID |
| `GIT_HUB_TOKEN` | GitHub personal access token |
| `GIT_HUB_ORGANIZATION_NAME` | GitHub organisation name |
| `AI_PROVIDER` | `claude_code` (no key needed) or `openai` |
| `OPENAI_API_KEY` | OpenAI API key (only if `AI_PROVIDER=openai`) |
| `HOME_WIFI` | Home WiFi SSID for automatic location detection |
| `OFFICE_WIFI` | Office WiFi SSID for automatic location detection |
| `EDITOR_APP` | macOS app to open notes (e.g. `Obsidian`) |
| `MANAGER_NAME` | Manager's name, used as default for 1-on-1 notes |
| `SCREEN_TIME_ENABLED` | `true` to enable macOS Screen Time integration (requires Full Disk Access) |
| `DAILY_ALARMS_ENABLED` | `true` (default) to create macOS Reminders on `wk daily start`; set to `false` to disable |

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency management and packaging

## Installation

### Local development setup

Install dependencies:

```bash
uv sync
```

Run the CLI:

```bash
uv run wk --help
```

### Build and install package

```bash
uv build
pip install dist/*.whl
wk --help
```

### Editable install (auto-reload on changes)

```bash
uv pip install -e .
wk --help
```

## Quick start

```bash
wk setup            # configure on first run
wk daily start      # create today's note
wk daily finish     # close the day
wk week report      # generate the weekly summary
wk doctor           # verify all integrations
```

## Development

Run tests:

```bash
uv run pytest
```

Run coverage:

```bash
uv run pytest --cov=taskjournal --cov-config=.coveragerc tests/
```

Pre-commit:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Poe tasks:

```bash
uv run poe format    # black
uv run poe lint      # mypy
uv run poe test      # pytest
uv run poe coverage  # coverage XML
uv run poe check     # format + test + coverage
```

## Documentation

- [Tool Overview](docs/tool-overview.md)
- [Jira Setup](docs/jira-setup.md)
- [Github Setup](docs/github-setup.md)
- [Changelog](docs/change-log.md)
