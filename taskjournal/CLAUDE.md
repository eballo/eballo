# taskjournal — Claude Code Guidelines

## Project overview

`taskjournal` is a Python CLI tool (`wk`) for managing engineering journals.
Stack: Python 3.12, Typer, Rich, dependency-injector, uv.

---

## Coding rules

### 1. Specific imports — never bare module imports

Always import specific names instead of importing the whole module:

```python
# WRONG
import os
import re
import uuid

# CORRECT
from os import makedirs, walk
from os.path import exists, join
from re import compile, IGNORECASE
from uuid import uuid4
```

`config.py` is an accepted exception — it uses `import os` for `os.getenv` as a bootstrap file.

### 2. No module-level config imports in services

Services must **never** import config values at module level.

```python
# WRONG — breaks testability, binds at import time
from taskjournal.config import JIRA_API_TOKEN
class JiraService:
    def __init__(self) -> None:
        self.token = JIRA_API_TOKEN

# CORRECT — config read once at container wiring time
class JiraService:
    def __init__(self, api_token: str, email: str, ...) -> None:
        self.token = api_token
```

The only place that should read from `taskjournal.config` is **`container.py`** and
**`cli/`** entry-points.

**Accepted exceptions** (OK to import at module level in services):
- Format/extension constants: `TEMPLATE_FORMAT`, `HOLIDAYS_FILE`, `FIREMAN_WEEKS_FILE`
- Path constants used to build runtime paths: `BASE_DIR`, `DAILY_NOTES_TEMPLATE`

**Must always be injected** (never imported directly in services):
- API secrets/tokens: `JIRA_API_TOKEN`, `GIT_HUB_TOKEN`, `OPENAI_API_KEY`
- User-configurable settings: `HOME_WIFI`, `OFFICE_WIFI`, `BACKUP_DIR`
- Organisation/identity values: `JIRA_ORGANIZATION`, `JIRA_EMAIL`, `GIT_HUB_ORGANIZATION_NAME`

### 2. All functions must have complete type annotations

Every parameter and every return value must be typed. No bare `Any` without a comment.

```python
# WRONG
def process(data, items):
    ...

# CORRECT
def process(data: dict[str, str], items: list[str]) -> bool:
    ...
```

### 3. Use Python 3.12+ type syntax

Never use `typing.List`, `typing.Dict`, `typing.Optional`, or `typing.Tuple`.

| Old (pre-3.10) | New (3.10+) |
|---|---|
| `List[str]` | `list[str]` |
| `Dict[str, int]` | `dict[str, int]` |
| `Optional[str]` | `str \| None` |
| `Tuple[int, str]` | `tuple[int, str]` |
| `Union[int, str]` | `int \| str` |

### 4. BaseService for every service

All services must extend `BaseService` and implement `health_check()` when they
depend on external resources or configuration.

```python
from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus

class MyService(BaseService):
    @property
    def name(self) -> str:
        return "MyService"

    def health_check(self) -> HealthCheckResult:
        ...
```

### 5. Use logger, never print()

```python
from taskjournal.services.logger import logger
logger.info(...)   # user-visible output
logger.debug(...)  # dev / verbose
logger.warning(...)
logger.error(...)
```

### 6. Dependency injection via AppContainer

Register every service in `AppContainer` (`container.py`) using:
- `providers.Singleton` for stateless utilities and services instantiated once.
- `providers.Factory` for services that need runtime arguments (e.g. year, filepath).

Never instantiate services with fallback logic (`service or ServiceClass()`). If a
dependency is required, declare it as a required `__init__` parameter.

### 7. No comments explaining WHAT the code does

Only add comments for WHY (hidden constraints, non-obvious invariants). Well-named
identifiers document themselves.

### 8. Async boundary — the CLI never calls service methods directly

The boundary is strict:

| Layer | Rule |
|---|---|
| **Services** | External I/O (Jira, GitHub, AI, HTTP) → `async def`. File I/O → `def`. |
| **CommandManager / domain classes** | Methods that `await` a service → `async def`. Pure file methods → `def`. |
| **CLI** | Always goes through `CommandManager`. Uses `run(m.method())` for `async` methods; calls sync methods directly. Never accesses `manager.jira`, `manager.github`, or `manager.ai_service` directly. |

```python
# WRONG — CLI bypassing CommandManager
service = get_manager(ctx).jira
tasks = run(service.get_current_sprint_tasks())

# CORRECT — CLI calls CommandManager, which owns the async boundary
tasks = run(get_manager(ctx).get_jira_tasks())
```

---

## Architecture

```
taskjournal/
  cli/           # Typer commands — thin wrappers that call CommandManager
  commands/      # CommandManager — orchestration layer
  services/      # Business logic — all extend BaseService
  repositories/  # Data formatters (TaskFormatter)
  models/        # Pure dataclasses / enums (Task, Status, Epic)
  parser/        # File parsing utilities
  container.py   # Dependency injection wiring
  config.py      # Reads .env — only referenced by container.py and cli/
  constants.py   # String constants shared across services
```

---

## Package manager

This project uses **uv** (not Poetry).

```bash
uv sync              # install deps
uv add <pkg>         # add runtime dependency
uv add --dev <pkg>   # add dev dependency
poe test             # run tests
poe lint             # mypy
poe format           # black
```

---

## Versioning

Managed by `bump-my-version`. To cut a release:

```bash
bumpversion minor    # 0.38.0 → 0.39.0
```

Always update `docs/change-log.md` with a summary before bumping.
