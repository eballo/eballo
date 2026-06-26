# Task Journal Tool Overview

Task Journal (`wk`) is a Python CLI to manage your day-to-day engineering journal.

It creates daily note files from templates, tracks work time, carries pending tasks forward, and generates weekly/monthly/half-year reports. It can also pull task context from Jira, contribution stats from GitHub, compute holiday/working-day statistics, and create backups of your notes.

## What It Does

- Creates daily notes with planned tasks and sprint context.
- Finalizes daily notes and calculates total time spent.
- Generates weekly, monthly, half-year, retrospective, and 1:1 report files.
- Integrates with Jira and GitHub services.
- Provides holiday and working-day statistics commands.
- Supports backup and legacy `.txt` to `.md` migration commands.

## Configuration

Task Journal loads environment variables from:

`~/.config/taskjournal/.env`

Create it from the sample file:

```bash
mkdir -p ~/.config/taskjournal
cp sample.env ~/.config/taskjournal/.env
```

Important variables:

- `BASE_DIR`: root folder where daily/weekly files are stored.
- `BASE_PROJECT`: path to this project's `taskjournal/` directory (used to load templates).
- `TEMPLATE_FORMAT`: `md` or `txt`.
- `JIRA_*`: Jira integration credentials/config.
- `GIT_HUB_*`: GitHub integration credentials/config.
- `OPENAI_API_KEY`: used for AI weekly summary generation.

## Usage

Show main help:

```bash
wk --help
```

### Daily workflow

```bash
wk daily start
wk daily start --date "2025-09-02 09:00" --force
wk daily finish
wk daily time
```

### Reports

```bash
wk week report
wk month report
wk half-year report
wk retro create
wk 1on1 report
```

### Holidays and statistics

```bash
wk holidays all --year 2026
wk holidays upcoming
wk holidays populate

wk statistics all --year 2026
wk statistics progress
wk statistics real
```

### Service and maintenance commands

These are hidden from default help but available:

```bash
wk services jira --mine
wk services git --stats --date 2026-01-01
wk backup run
wk migrate daily <path-to-file-or-directory>
```
