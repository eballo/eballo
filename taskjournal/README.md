# Task Journal

TaskJournal CLI is a lightweight command-line tool that helps you manage your daily work notes, track working hours, and generate weekly retrospectives and summaries. It's built to support a structured journaling workflow to improve personal productivity and accountability.

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

# How to use it
```bash
> wk --help

 Usage: wk [OPTIONS] COMMAND [ARGS]...

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ daily-start                                                                                                                                      │
│ daily-finish                                                                                                                                     │
│ retro                                                                                                                                            │
│ week-summary                                                                                                                                     │
│ time                                                                                                                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
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

## Versions

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
