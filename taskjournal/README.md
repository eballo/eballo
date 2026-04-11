# Task Journal

[![Version](https://img.shields.io/badge/version-0.31.0-blue.svg)](#task-journal)
[![Python](https://img.shields.io/badge/python-3.12%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/deps-poetry-60A5FA.svg?logo=poetry&logoColor=white)](https://python-poetry.org/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC.svg?logo=pytest&logoColor=white)](https://docs.pytest.org/)

Task Journal (`wk`) is a Python CLI to manage your day-to-day engineering journal.

For the full explanation of features, configuration, and command examples, see:
[Tool Overview](wiki/tool-overview.md)

## Requirements

- Python 3.12+
- Poetry (for dependency and environment management)

## Installation

### Local development setup

Creation of the environment
```bash
python -m venv venv
source venv/bin/activate
pip install poetry
```

```bash
poetry install
```

Run the CLI with Poetry:

```bash
poetry run wk --help
```

Or use the local virtualenv binary directly if available:

```bash
./venv/bin/wk --help
```

### Build and install package

```bash
poetry build
pip install dist/*.whl
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
poetry run pytest
```

Run coverage:

```bash
poetry run pytest --cov=taskjournal --cov-config=.coveragerc tests/
```

Pre-commit:

```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

Poe tasks:

```bash
poe format       # black
poe test         # pytest
poe coverage     # coverage XML
poe check        # format + test + coverage
```

## Documentation

- [Tool Overview](wiki/tool-overview.md)
- [Jira Setup](wiki/jira-setup.md)
- [Github Setup](wiki/github-setup.md)
- [Changelog](wiki/change-log.md)
