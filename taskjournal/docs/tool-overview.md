# Task Journal Tool Overview

Task Journal (`wk`) is a Python CLI to manage your day-to-day engineering journal.

It creates daily note files from templates, tracks work time, carries pending tasks forward, and generates weekly/monthly/quarterly/half-year/yearly reports. It can also pull task context from Jira, contribution stats from GitHub, compute holiday/working-day statistics, and create recoverable backups of your notes.

## What It Does

- Creates daily notes with planned tasks and sprint context.
- Finalizes daily notes and calculates total time spent.
- Generates weekly, monthly, quarterly, half-year, yearly, retrospective, and 1:1 report files.
- Integrates with Jira and GitHub services.
- Provides holiday and working-day statistics commands.
- Supports backup verification, safe restore, and legacy `.txt` to `.md` migration commands.

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
- `BACKUP_DIR`: location of backup ZIP files.
- `TEMPLATE_FORMAT`: `md` or `txt`.
- `JIRA_*`: Jira integration credentials/config.
- `GIT_HUB_*`: GitHub integration credentials/config.
- `AI_PROVIDER`: `claude_code` or `openai`.
- `OPENAI_API_KEY`: required only for the OpenAI provider.

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
wk daily check
wk doctor
```

`wk daily check` returns a nonzero exit code for missing or incomplete notes; `wk doctor` does so for error-level checks (warnings alone do not fail). Both can be used in scripts.

### Reports

```bash
wk week report
wk report month
wk report quarter
wk report half-year
wk report year
wk report retro
wk report 1on1 create
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

```bash
wk services jira --mine
wk services git --stats
wk search -q "keyword"                 # searches both .md and historical .txt notes
wk backup run
wk backup verify /path/to/backup.zip
wk backup restore /path/to/backup.zip   # preview, then confirm; skips existing files
wk backup restore /path/to/backup.zip --yes  # noninteractive confirmation
wk migrate daily <path-to-file-or-directory>
```

Restoration checks ZIP integrity and entry paths before writing to `BASE_DIR`. Existing notes are never overwritten; run `verify` first if you only want to validate the archive.
