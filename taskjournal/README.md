# 🗓️ Task Journal

[![Version](https://img.shields.io/badge/version-0.56.0-blue.svg)](#task-journal)
[![Python](https://img.shields.io/badge/python-3.12%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/deps-uv-DE5FE9.svg?logo=astral&logoColor=white)](https://docs.astral.sh/uv/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC.svg?logo=pytest&logoColor=white)](https://docs.pytest.org/)

Task Journal (`wk`) is a Python CLI to manage your day-to-day engineering journal.

It helps you:
- create and finalize daily notes from templates
- track time spent and working days
- carry pending tasks forward between days/weeks
- generate weekly, monthly, half-year, retrospective, and 1:1 reports
- generate AI-assisted summaries
- pull context from Jira and GitHub
- compute holidays and working-day statistics
- create backups and migrate legacy files

For the full explanation of features, configuration, and command examples, see:
[Tool Overview](docs/tool-overview.md)

## Features

### Daily workflow
- `wk daily start` — create a daily note from a template, carrying pending tasks forward
- `wk daily finish` — finalize the day and calculate total time spent
- `wk daily status` — show elapsed time, task breakdown, and finalization state for today
- `wk daily check` — validate the structure and completeness of today's note
- `wk daily audit` — scan all notes for a year and list incomplete ones (`--fix` opens files in `$EDITOR`)
- `wk daily sync` — pull current Jira tasks and add any missing ones to today's note
- `wk daily task add/done/block/list` — manage tasks directly from the CLI
- `wk daily start --offline` — skip all Jira and GitHub API calls

### Reports
- `wk week report` — weekly summary (warns if any daily note is incomplete)
- `wk week list` — list daily notes for a week with their status and time logged
- Monthly, half-year, and retrospective reports
- 1:1 report with `wk 1on1 add-topic` to append topics from the CLI

### Statistics and calendar
- `wk statistics streak` — consecutive journaling streak and all-time record
- Holiday listing, upcoming holidays, and working-day statistics
- Progress and real-time statistics

### Integrations
- Jira task context
- GitHub contribution statistics
- AI summary generation

### Search
- `wk search` — search by keyword across all notes with `--from`, `--to`, and `--type` filters

### Configuration and maintenance
- `wk setup` — interactive configuration wizard
- `wk doctor` — full health check of configuration and external integrations
- `wk info` — show `BASE_DIR`, template format, and integration status
- Backup notes and migrate legacy `.txt` files to `.md`
- Templates in Markdown and plain text

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
wk --help
wk daily start
wk daily finish
wk week report
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
uv run poe test      # pytest
uv run poe coverage  # coverage XML
uv run poe check     # format + test + coverage
```

## Documentation

- [Tool Overview](docs/tool-overview.md)
- [Jira Setup](docs/jira-setup.md)
- [Github Setup](docs/github-setup.md)
- [Changelog](docs/change-log.md)
