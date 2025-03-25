# Task Journal

TaskJournal CLI is a lightweight command-line tool that helps you manage your daily work notes, track working hours, and generate weekly retrospectives and summaries. It's built to support a structured journaling workflow to improve personal productivity and accountability.

## Install
we are using virtualenv inside the project. When we install the dependencies it will install the dependencies 
inside the virtualenv.
```bash
poetry install
source .venv/bin/activate
```
Create a symbolic link
sudo ln -s /Users/eballo/Documents/work/personal/eballo/taskjournal/taskjournal/main.py /usr/local/bin/wk

### Configure .env
```bash
cp sample.env .env
```

### Run Tests
```bash
poetry run pytest
```
### Run the code coverage
```bash
poetry run pytest --cov=taskjournal --cov-config=.coveragerc tests/
```

# How to use it
```bash
> wk --help
usage: wk [-h] [--debug] {daily-start,daily-finish,retro,week-summary,time}

Daily Task Tracker Command Line Tool

positional arguments:
  {daily-start,daily-finish,retro,week-summary,time}
                        Command to execute.

options:
  -h, --help            show this help message and exit
  --debug               Enable debug mode for additional logging.
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
