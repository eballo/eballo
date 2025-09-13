# Task Journal

TaskJournal CLI is a lightweight command-line tool that helps you manage your daily work notes, track working hours, and
generate weekly retrospectives and summaries. It's built to support a structured journaling workflow to improve personal
productivity and accountability.

## Install

```bash
poetry install
source .venv/bin/activate
poetry build
pip install .

wk --help
```

After install it you can do wk --shell-completion to get the shell completion script.

## Local Development

```bash
poetry install
source .venv/bin/activate
```

### Configure .env

Copy the sample environment file to `.env` and update the values as needed.
Needs to be placed in ~/config/taskjournal/.env

```bash
cp sample.env .env
```

### Run the tests

```bash
poetry run pytest
```

### Run the code coverage

```bash
poetry run pytest --cov=taskjournal --cov-config=.coveragerc tests/
```

### Pre-commit

```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

### with poe

```bash
poe format       # runs black
poe test         # runs pytest
poe coverage     # runs coverage with HTML report
poe check        # runs everything
```

# How to use it

```bash
> wk
Usage: wk [OPTIONS] COMMAND [ARGS]...

 Task Journal CLI.
 A CLI tool to organize your work by managing notes, summaries, reports.
 Helping you stay on track and communicate progress effectively.
 Use --help on any command to see detailed options and examples.

╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --version                     Show the application version and exit.                                            │
│ --debug                       Enable debug logging (verbose output).                                            │
│ --install-completion          Install completion for the current shell.                                         │
│ --show-completion             Show completion for the current shell, to copy it or customize the installation.  │
│ --help                        Show this message and exit.                                                       │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ daily       Daily workflow commands (start, finish).                                                            │
│ week        Weekly reporting commands.                                                                          │
│ month       Monthly reporting commands.                                                                         │
│ half-year   Half-year reporting commands.                                                                       │
│ retro       Create a Retrospective                                                                              │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

```

## Daily Start

```bash
> wk daily start
```

## Daily Finish

```bash
> wk daily finish
```

## Retro

```bash
> wk retro report
```

## Week Summary

```bash
> wk week report
```

## Haff-Year Review

```bash
> wk half-year report
```

## Time

```bash
> wk daily time
```

## Backup

```bash
> wk backup run
```

## Jira

```bash
> wk services jira
```

## version

```bash
> wk --version
```

## Wiki

- [Jira Setup](wiki/jira-setup.md)
- [Github Setup](wiki/github-setup.md)
- [Shell Completion](wiki/shell-completion.md)

## Versions

# 0.8.0

- Improve Jira Service
    - Improve logging if it doesn't exist
    - migrate to version 3 jsql
    - migrate to httpx to use async calls
- update services to use async calls

# 0.7.0

- Big refactor for cli (better structure and better organization for the commands)
- Introduce the CommandManager class + services

**Note** the versions do not match the github releases versions they start to be aligned from 0.5.0

### 0.6.0

- Add md template support

### 0.5.0

- Add github integration service

### 0.4.0

- Add backup command
- Jira integration
- Improve Templates (dailyNotes, retro, weeklysummary)
- daily-start with force option
- daily-finish with force option
- daily-start for a given date
- daily-finish for a given date
- Created Task model (pydantic) + refactor

### 0.3.0

- add daily-finish custom date update

### 0.2.0

- install package properly
- added proper packages

### 0.1.0

- Initial release
- Add daily start
- Add daily finish
- Add retro
- Add week summary
- Add time
- tests + code coverage
- pre-commit
- shell completion
