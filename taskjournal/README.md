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
> wk --help

 Usage: wk [OPTIONS] COMMAND [ARGS]...

╭─ Options ──────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                    │
╰────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────╮
│ daily-start                                                                    │
│ daily-finish                                                                   │
│ retro                                                                          │
│ week-summary                                                                   │
│ half-year-review                                                               │
│ time                                                                           │
│ backup                                                                         │
│ version                                                                        │
│ git                                                                            │
│ jira                                                                           │
╰────────────────────────────────────────────────────────────────────────────────╯
```

## Daily Start

```bash
> wk daily-start
```

## Daily Finish

```bash
> wk daily-finish
```

## Retro

```bash
> wk retro
```

## Week Summary

```bash
> wk week-summary
```

## Haff-Year Review

```bash
> wk half-year-review
```

## Time

```bash
> wk time
```

## Backup

```bash
> wk backup
```

## Jira

```bash
> wk jira
```

## version

```bash
> wk version
```

## Wiki

- [Jira Setup](wiki/jira-setup.md)
- [Github Setup](wiki/github-setup.md)
- [Shell Completion](wiki/shell-completion.md)

## Versions

### 0.6.0

- Add md template support

### 0.5.0

- Add github integration service

### 0.4.0 - mix of features

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
