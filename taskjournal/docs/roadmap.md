# Task Journal — Roadmap

> Based on analysis of the current codebase (v0.37.0). Organised into four horizons: foundational technical improvements, new features, extended features, and long-term ideas.

---

## Horizon 1 — Technical improvements and technical debt

These improvements add no visible functionality but make the code more robust, consistent, and easier to maintain.

### 1.1 More robust parser

**Current problem:** `DailyParserService._parse_content` detects sections by substring matching (`"Planned Tasks" in line`). If the template changes slightly, the parser fails silently.

**Proposal:** Define section headers as centralised constants (or regex), shared between the parser and the templates, so they are always consistent.

---

### 1.2 Template system consistency

**Current problem:** The project mixes two substitution systems:
- `Jinja2` for `daily start` (daily notes)
- `str.replace("{{placeholder}}", value)` for week/month/half-year

**Proposal:** Migrate all templates to Jinja2. Remove `_apply_replacements` and all calls to `str.replace` with manual placeholders.

---

### 1.3 `GithubService` as a context manager

**Current problem:** `GithubService` creates an `httpx.AsyncClient` in `__init__` and requires calling `await self.github.close()` manually. Some commands call it (month, half-year) but others don't, and it's easy to forget.

**Proposal:** Implement `__aenter__` / `__aexit__` or use `asynccontextmanager` and manage the client lifecycle from `CommandManager` with `async with`.

---

### 1.4 Incomplete task statuses in the parser

**Current problem:** The parser maps `[ ]` → TODO, `[x]` → DONE and `[-]` → BLOCKED, but there is no textual representation for `IN_PROGRESS` or `CODE_REVIEW`. Tasks with these statuses cannot be correctly persisted in the file and are lost when reading.

**Proposal:** Define standard characters for all statuses (`[>]` for IN_PROGRESS, `[~]` for CODE_REVIEW) and update the parser, formatter, and templates.

---

### 1.5 "Legacy" ID in the parser

**Current problem:** When the parser creates `Task` objects, it assigns `id="legacy"` (string literal) instead of a real UUID (`services/parser.py:152`).

**Proposal:** Generate a `uuid4()` for each parsed task, as `TaskManager.create_task` does.

---

### 1.6 AI service abstraction

**Current problem:** `OpenAIService` directly calls `api.openai.com` with the model `gpt-4o-mini` hardcoded. If you want to switch providers (Claude, Gemini, Ollama for local use) you need to modify the class.

**Proposal:** Define an `AIService` interface with a `summarize(...)` method and interchangeable implementations. Allow configuring the provider and model via `.env` (`AI_PROVIDER=openai|claude|ollama`, `AI_MODEL=...`).

---

### 1.7 Improve `wk info`

**Current problem:** `wk info` only shows the day and week number.

**Proposal:** Show the status of all integrations (Jira connected / not configured / error, GitHub connected, OpenAI configured, BASE_DIR path, active template format). Useful for diagnosing configuration issues.

---

### 1.8 Previous-day completion check on `wk daily start`

**Current problem:** `wk daily start` creates a new note even if the previous day's note was never finalised (missing end time or daily summary). This silently allows gaps in the journal.

**Proposal:** Before creating a new note, check whether the most recent existing note has been finalised. If not, print a clear warning listing what is missing (end time, summary section) so the user can finish the previous day before continuing.

---

### 1.9 Incomplete-day warnings in `wk week report`

**Current problem:** `wk week report` generates the report regardless of whether all daily notes for the week are fully finalised, silently producing incomplete summaries.

**Proposal:** Before generating the report, scan each daily note for the week and warn if any are missing an end time or a daily summary. The report is still generated but the warning makes the gap visible.

---

### 1.10 Smarter deduplication when carrying tasks forward

**Current problem:** When `wk daily start` carries tasks forward it calls `TaskManager.unique_tasks()`, which deduplicates only by exact description match. Duplicates still slip through when:
- A Jira task pulled from the API has a slightly different description than the same task already in the previous day's note (e.g. trailing whitespace, casing, or Jira key prefix stripped).
- A task appears in both `previous_pending_tasks` (same week) and `last_week_pending_tasks` (Monday carry-over) at the same time.
- A pending task from the note and a current-sprint Jira task refer to the same ticket but with different text.

**Proposal:** Improve deduplication by normalising descriptions before comparison (strip, lowercase) and by matching on Jira key when available, so two tasks with the same `key` are never both included regardless of description differences.

---

### 1.11 CLI command reorganisation

**Current problem:** The CLI has grown organically and now shows several structural issues:

- `daily.py` is a 543-line monolith mixing three unrelated concerns: time tracking (`start`, `finish`, `time`, `status`), note quality (`check`, `audit`, `sync`), and task management (the nested `task` sub-typer with `list`, `add`, `done`, `block`, `wip`).
- Four near-empty report files (`month.py`, `half_year.py`, `retro.py`, `one_on_one.py`, 25–43 lines each) each wrap a single command and live as separate top-level groups.
- The "Tools" `help_panel` contains 10 unrelated entries: setup wizard, health check, backup, migration, fireman schedule, holidays, statistics, AI services, search, and info.

**Proposal:** Restructure into five focused panels:

```
📋 Daily workflow
  wk daily   → start, finish, time, status, check, sync, audit

📝 Tasks  (promoted from daily sub-typer to top-level)
  wk task    → list, add, done, block, wip

📊 Reports
  wk week    → report, recreate-since, list  (unchanged)
  wk report  → month, half-year, retro, 1on1  (NEW — replaces 4 separate groups)
  wk statistics → all, progress, real, streak  (moved here from Tools)

📅 Calendar
  wk holidays → list, upcoming, next, add, populate
  wk fireman  → add, list, upcoming, summary

🔧 Admin
  wk setup · wk doctor · wk backup · wk migrate

🛠️ Tools
  wk services → jira, git, claude
  wk search · wk info
```

**Concrete changes:**

1. Extract the `task` sub-typer out of `daily.py` into a new `taskjournal/cli/commands/task.py` and register it as `wk task` at the root level. `daily.py` drops from ~543 to ~280 lines.
2. Create `taskjournal/cli/commands/report.py` with subcommands `month`, `half-year`, `retro`, `1on1`. Delete the four individual files. Breaking change: `wk month` → `wk report month`, `wk half-year` → `wk report half-year`, `wk retro` → `wk report retro`, `wk 1on1` → `wk report 1on1`.
3. Move `statistics` from the `🗂️ Tools` panel to `📊 Reports` in `cli.py` (one-line change).
4. Add a `📅 Calendar` `rich_help_panel` to the `holidays` and `fireman` registrations in `cli.py`.
5. Add a `🔧 Admin` `rich_help_panel` to the `setup`, `doctor`, `backup`, and `migrate` registrations in `cli.py`.
6. Update all affected tests that invoke commands via the old top-level names.

**Net result:** 16 CLI files → 13 files. "Tools" shrinks from 10 entries to 3. Top-level `wk --help` goes from one overloaded panel to five panels with clear purpose.

---

### 1.12 Split `CommandManager` into domain-specific classes

**Current problem:** `commandmanager` in `commands/commands.py` is a ~900-line God Object handling every domain of the application: daily notes, weekly/monthly/half-year reports, 1on1s, retros, search, statistics, streaks, Jira sync, GitHub integration, backup, AI summaries... Every new feature adds more methods to the same class. Finding relevant code requires scrolling through an oversized file with no clear boundaries.

Note: this is distinct from 1.11 (CLI reorganisation). 1.11 fixes the `cli/commands/` layer; 1.12 fixes the `commands/` orchestration layer below it.

**Proposal:** Split into domain-specific classes inside `commands/`:

```
commands/
  daily.py        ← DailyCommands   (start, finish, check, audit, sync)
  reports.py      ← ReportCommands  (week, month, half-year, retro, 1on1)
  statistics.py   ← StatsCommands   (streak, working days, progress)
  search.py       ← SearchCommands  (search_notes)
  tasks.py        ← TaskCommands    (task CRUD, carry-forward)
```

Each class receives only the services it actually needs. `AppContainer` wires them individually. The CLI context object keeps a reference to each, or a lightweight facade delegates to the right class.

---

### 1.13 Parser should return typed models, not raw dicts

**Current problem:** `DailyParserService.parse()` returns `dict[str, Any]`. Callers access fields like `data.get("time_spent", "")`, `data.get("summary", [])`, `data.get("tasks", [])` with string keys and no type safety. A typo in a key silently returns `None`; there is no autocomplete or static analysis support.

**Proposal:** Define a `ParsedNote` dataclass (or Pydantic model) in `models/`:

```python
@dataclass
class ParsedNote:
    time_spent: str
    summary: list[str]
    tasks: list[Task]
    start_time: str | None
    end_time: str | None
```

`DailyParserService.parse()` returns `ParsedNote | None`. All callers use typed attributes (`note.time_spent`, `note.summary`) instead of dict lookups. Existing `Task` and `Status` models are already in place — this closes the gap.

---

### 1.14 Unify the async model

**Current problem:** The codebase mixes sync and async inconsistently:
- `create_daily_notes` is `async` (needs Jira/GitHub)
- `finalize_daily_notes` is sync
- `audit_daily_notes`, `audit_weekly_coverage` are sync
- The CLI bridges async calls with `run(m.create_daily_notes(...))` in some places and calls sync methods directly in others

This makes it hard to reason about blocking behaviour and complicates adding new features that mix both.

**Proposal:** Establish a clear rule — external I/O (Jira, GitHub, AI, HTTP) lives in `async` service methods; file I/O stays sync. `CommandManager` methods that call async services are `async`; purely file-based methods are sync. The CLI always uses `run()` for async command methods and calls sync ones directly. Document the boundary explicitly in `CLAUDE.md`.

---

### 1.15 Register `HolidayService` in the DI container

**Current problem:** `HolidayService` is instantiated manually inside `CommandManager` methods using a local `holiday_cache` dict to avoid re-reading the file on each call (e.g. `commands.py:751`). This bypasses the DI container entirely: the service cannot receive injected config, cannot be mocked in tests without patching internals, and the caching logic is duplicated across methods.

**Proposal:** Register `HolidayService` as a `providers.Factory` in `AppContainer` (keyed by year, or with the filepath as a parameter). Methods that need it receive it via injection. The caching responsibility moves to the container or to a single lazy-loaded property on the service.

---

### 1.17 Full `.txt` format support and test coverage

**Current problem:** `TEMPLATE_FORMAT` can be `md` or `txt` but `.txt` mode is broken in several places and has no dedicated tests. The project appears to have migrated from `.txt` to `.md` as the default (there is even a `migration.py` that converts `.txt` → `.md`), but the `.txt` path was never fully cleaned up or verified.

**Known breakages when `TEMPLATE_FORMAT=txt`:**

| Location | Problem |
|---|---|
| `config.py:19` | `HOLIDAYS_FILE = "holidays/holidays.md"` — hardcoded, ignores `TEMPLATE_FORMAT` |
| `config.py:20` | `FIREMAN_WEEKS_FILE = "fireman/fireman_weeks.md"` — same |
| `services/setup.py:115-116` | Creates `holidays.md` and `fireman_weeks.md` always as `.md` during `wk setup` |
| `services/holidays.py:189` | `DailyNotes-Holidays.md` hardcoded — replace with `TEMPLATE_FORMAT` |
| `commands/commands.py:157` | `audit_weekly_coverage` checks only `.md` for holiday files — update to use `TEMPLATE_FORMAT` |

**Proposal:**

1. Make `HOLIDAYS_FILE` and `FIREMAN_WEEKS_FILE` in `config.py` respect `TEMPLATE_FORMAT`:
   ```python
   HOLIDAYS_FILE = f"holidays/holidays.{TEMPLATE_FORMAT}"
   FIREMAN_WEEKS_FILE = f"fireman/fireman_weeks.{TEMPLATE_FORMAT}"
   ```
2. Fix `setup.py` to create the holidays and fireman config files with the correct extension.
3. Fix `HolidayService.populate_files()` — replace hardcoded `.md` extension with `TEMPLATE_FORMAT`:
   ```python
   filename = f"{date_obj}-DailyNotes-Holidays.{TEMPLATE_FORMAT}"
   ```
4. Audit the parser (`services/parser.py:165`) to confirm `.txt` parsing is complete and correct.
5. Add a dedicated test suite that runs all key commands (`daily start`, `daily finish`, `week report`, `wk daily audit`, `wk statistics`) with `TEMPLATE_FORMAT=txt` mocked, verifying file names, content, and coverage checks all use the right extension.

**Why this matters:** if a user has configured `TEMPLATE_FORMAT=txt`, the tool silently creates files with the wrong extension, then fails to find them. It is a configuration that appears to work but produces broken output.

---

### 1.18 Template review and reorganisation

A full audit of all 12 template files (6 templates × md + txt) revealed multiple problems that need fixing independently of any new feature work.

**Problems found:**

**`dailyNotes.txt` is broken** — comparing against `dailyNotes.md`:

| Issue | `.txt` | `.md` |
|---|---|---|
| Start time variable | `{{time}}` ❌ | `{{start_time}}` ✓ |
| End Time | blank literal | `{{end_time}}` ✓ |
| Time Spent | blank literal | `{{time_spent}}` ✓ |
| Break field | missing entirely | `{{break_time}} lunch` ✓ |
| Work from | duplicated (raw + conditional) | conditional only ✓ |
| Notes, Summary, Extra | missing | present ✓ |
| Section separators | missing | `---` ✓ |

**`.md` / `.txt` divergence across all templates** — `halfYear.txt` (69 lines of verbose prose) vs `halfYear.md` (117 lines with structured headers): they produce fundamentally different documents. All `.txt` files need to mirror their `.md` counterpart in structure and variables, just without markdown syntax.

**Dead code: `DAILY_NOTES_END_TEMPLATE`** — defined in `config.py` but never imported or called anywhere.

**Hardcoded template strings in `setup.py`** — `_HOLIDAYS_TEMPLATE` and `_FIREMAN_TEMPLATE` are inline Python strings. Users cannot customise the initial structure without editing source code.

**`1on1.md/.txt` has zero Jinja2 variables** — every 1on1 file is created with identical static content; no date, no person name, no meeting number is rendered.

---

**Proposed changes:**

1. **Rewrite `dailyNotes.txt`** to be a correct plain-text mirror of `dailyNotes.md` with all missing variables restored and the duplicate `Work from` block removed.

2. **Sync all other `.txt` templates** to their `.md` counterparts — same variables, same sections, same order; only formatting markers differ (no `**`, no `#`, blank lines instead of `---`). Affects: `weekSummary.txt`, `month.txt`, `halfYear.txt`, `retro.txt`, `1on1.txt`.

3. **Remove `DAILY_NOTES_END_TEMPLATE`** from `config.py` — dead code, never referenced.

4. **Extract hardcoded templates to files:**
   - Create `templates/md/holidays.md` and `templates/txt/holidays.txt` from `_HOLIDAYS_TEMPLATE`
   - Create `templates/md/fireman_weeks.md` and `templates/txt/fireman_weeks.txt` from `_FIREMAN_TEMPLATE`
   - Add `HOLIDAYS_TEMPLATE` and `FIREMAN_WEEKS_TEMPLATE` constants to `config.py`
   - Update `setup.py` to load from file and render with Jinja2 (`{year}` variable)

5. **Add dynamic variables to `1on1`** — add `{{date}}` and `{{person_name}}` to the top of both `1on1.md` and `1on1.txt`. Update `create_one_on_one()` in `commands.py` to render with `Template().render()` (currently uses the file as-is with no render call).

**Files to create or modify:**

| File | Action |
|---|---|
| `templates/txt/dailyNotes.txt` | Full rewrite to match `.md` |
| `templates/txt/weekSummary.txt` | Sync with `.md` |
| `templates/txt/halfYear.txt` | Full rewrite to match `.md` |
| `templates/md/1on1.md` | Add `date`, `person_name` variables |
| `templates/txt/1on1.txt` | Sync with `.md` |
| `templates/txt/month.txt` | Sync with `.md` |
| `templates/txt/retro.txt` | Sync with `.md` |
| `templates/md/holidays.md` *(new)* | Extracted from `setup.py` |
| `templates/txt/holidays.txt` *(new)* | Plain text equivalent |
| `templates/md/fireman_weeks.md` *(new)* | Extracted from `setup.py` |
| `templates/txt/fireman_weeks.txt` *(new)* | Plain text equivalent |
| `taskjournal/config.py` | Remove `DAILY_NOTES_END_TEMPLATE`; add `HOLIDAYS_TEMPLATE`, `FIREMAN_WEEKS_TEMPLATE` |
| `taskjournal/services/setup.py` | Load holidays/fireman from template files |
| `taskjournal/commands/commands.py` | Render `1on1` with `Template().render()`, pass `date` and `person_name` |

**Content improvements (apply to both `.md` and `.txt` for each template):**

**`halfYear.md/.txt` — fix "past month" bug:**
The Reflection Questions section was copied from `month.md` and never updated — all six questions say "past month" instead of "past 6 months" or "past half year". Replace throughout.

**`retro.md/.txt` — enrich with structure:**
Current template is four empty sections with no guidance. Replace with:
- `## 📊 Sprint metrics` — add `Velocity:`, `Completed:`, `Carried over:` fields
- `## ✅ What Went Well` — keep, add example bullet
- `## ⚠️ What Didn't Go Well` — keep, add example bullet
- `## 💡 What to Try Next Sprint` — rename from "Areas for Improvement" to be action-oriented
- `## 🎯 Action Items` — keep, add 3 placeholder checkboxes instead of one

**`1on1.md/.txt` — rewrite with logical meeting structure:**
Current content is confusing ("Proposal topics", "Doing self-review" as body text). Replace with a clear flow:

```
## 📋 Follow-up from last meeting
- [ ] (action item from previous 1on1)

## 📌 Topics to discuss
- How do you see me progressing?
- Is there room where I can help you more?
- Any feedback for me?
- Anything you want to share?
- Anything to improve in our 1on1s?

## 💬 Notes

## 🎯 Action Items
- [ ]

## 🔜 Topics for next time
```

---

### 1.19 Separate user output from logger

**Current problem:** `logger.info()` is used throughout the codebase for messages that are the direct response to the user — confirmations, results, summaries:

```python
logger.info(f"Daily notes finalized {daily_notes_file}")
logger.info(f"Week summary file created at: {summary_file}")
logger.info("Coverage: all week folders have 5 files (daily or holiday).")
```

These are not operational logs — they are user-facing output. Using `logger.info()` for this mixes two distinct concepts and causes real problems:

- If the logger is configured to filter `INFO` level or redirect stderr to a file, the user sees nothing.
- `wk daily finish | grep finalized` is unreliable if the output goes through the logging system instead of stdout.
- `--debug` should add diagnostic detail on top of what the user already sees, not control what the user sees at all.
- The output format is inconsistent: some messages go through Rich `console.print()` (tables, panels, coloured text) and others go through `logger.info()` (plain or log-formatted text).

**Correct separation:**

| Message type | Should use |
|---|---|
| Result / confirmation to the user | `console.print("[green]✓[/green] ...")` |
| Structured data (tables, panels) | `console.print(Table(...))` |
| Warnings the user must see | `logger.warning(...)` (keep — these are real warnings) |
| Errors | `logger.error(...)` (keep) |
| Diagnostic / developer detail | `logger.debug(...)` — only visible with `--debug` |

**Proposal:** Audit every `logger.info()` call across `commands/` and `cli/commands/` and replace with `console.print()` using appropriate Rich markup. Reserve `logger.info()` only for messages that are genuinely informational noise the user does not need unless debugging. The `console` instance is already present in every CLI command file.

**Scope:** approximately 40–50 `logger.info()` calls to review across `commands/commands.py` and all `cli/commands/*.py` files.

---

## Horizon 2 — New features

Features that bring direct value to the daily workflow.

### 2.1 `wk daily status`

Show a summary of the current day's status: elapsed time, completed vs. pending tasks, and whether the day has been finalised.

```bash
wk daily status
# Today: Thursday 2026-06-25
# Time elapsed: 4h 23m  |  Est. finish: 17:30
# Tasks: 3 done / 2 pending / 1 blocked
```

---

### 2.2 `wk daily task add` and `wk daily task done`

Manage tasks from the CLI without opening the file manually.

```bash
wk daily task add "Review Maria's PR"
wk daily task done "Review Maria's PR"
wk daily task list
```

The command modifies the current day's note file directly.

---

### 2.3 `wk search`

Search by keyword across all note and report files.

```bash
wk search "authentication"
wk search "authentication" --from 2026-01-01 --to 2026-06-30
wk search "authentication" --type daily
```

Useful for recovering context from past decisions or finding when something was worked on.

---

### 2.4 `wk statistics streak`

Show the streak of consecutive days of recorded work, the all-time record, and consistency statistics.

```bash
wk statistics streak
# Current streak: 12 days
# Longest streak: 34 days (2025-03-01 → 2025-04-03)
```

---

### 2.5 `wk 1on1 add-topic`

Add a topic to the next 1:1 session from the CLI, without opening the file.

```bash
wk 1on1 add-topic "Discuss Q3 career plan"
wk 1on1 add-topic "Blocker with prod access"
```

Accumulates topics in the current open 1:1 file or creates a new one if it doesn't exist.

---

### 2.6 Explicit offline mode

**Current problem:** When Jira or GitHub are not configured, they fail silently and return empty lists. There is no way to know if it's a configuration problem or if there is simply no data.

**Proposal:** Detect at startup whether integrations are configured (`JIRA_API_TOKEN != "your-jira-key"`, etc.) and show clear warnings. Add a `--offline` flag to skip all external calls.

```bash
wk daily start --offline
```

---

### 2.7 `wk week list`

List the files for the current week (or a given date) with their status (open, finalised).

```bash
wk week list
wk week list --date 2026-06-01
# Mon 2026-06-23: ✓ finalized (8h 12m)
# Tue 2026-06-24: ✓ finalized (7h 45m)
# Wed 2026-06-25: ○ open
```

---

### 2.8 `wk daily check`

Validate that the day's note file has the correct format: metadata fields present, task section parseable, consistent times.

```bash
wk daily check
# ✓ Metadata: OK
# ✓ Tasks section: 5 tasks found
# ⚠ End time missing (not finalized)
# ✓ Format: md
```

---

### 2.9 `wk daily audit`

Scan all finished daily notes and report which ones are missing a start time, end time, or daily summary. Useful for finding gaps in historical records.

```bash
wk daily audit
# ⚠ 2026-05-12: missing end time
# ⚠ 2026-06-03: missing daily summary
# ✓ 47 notes OK

wk daily audit --year 2026
wk daily audit --fix   # open each offending file in $EDITOR
```

---

### 2.10 macOS alarm on `wk daily start`

When `wk daily start` creates a new daily note, schedule a macOS alarm (via `osascript` or `at`) set to fire at the calculated end time so the user gets a system notification when the workday is expected to finish.

```bash
wk daily start
# Daily note created for 2026-06-27
# ⏰ Alarm set for 18:00 — end of scheduled workday
```

The alarm time is derived from the start time plus the configured working hours. If the alarm cannot be scheduled (e.g. not on macOS), the command continues silently.

---

### 2.12 `wk daily sync`

Pull the latest Jira tasks assigned to the user and add any that are missing from the current day's note. Keeps the note in sync without manual copy-paste.

```bash
wk daily sync
# Fetching Jira tasks...
# Added: PROJ-101 — Fix login timeout
# Added: PROJ-104 — Update API docs
# Already present: PROJ-98
```

Only adds tasks with status `In Progress` or `To Do` by default; a `--all` flag includes everything assigned.

---

### 2.13 `wk doctor`

Run a full health check of the tool's configuration and external integrations, then print a final summary of what is working, what is misconfigured, and what is missing.

Checks performed:

- **Config file** — `~/.config/taskjournal/.env` exists and all required variables are set
- **Paths** — `BASE_DIR`, `BASE_PROJECT`, and `BACKUP_DIR` exist and are readable/writable
- **Template format** — `TEMPLATE_FORMAT` is `md` or `txt` and the corresponding templates are present
- **Jira** — credentials are set, connection succeeds, board ID resolves
- **GitHub** — token is set, connection succeeds, organisation resolves
- **OpenAI** — API key is set, a lightweight test call succeeds
- **WiFi detection** — `HOME_WIFI` and `OFFICE_WIFI` are set

```bash
wk doctor
# Checking configuration...
#   ✓ Config file found: ~/.config/taskjournal/.env
#   ✓ BASE_DIR exists and is writable
#   ✓ Templates (md) found
#
# Checking integrations...
#   ✓ Jira: connected (org: my-org, board: 42)
#   ✓ GitHub: connected (org: my-github-org)
#   ⚠ OpenAI: API key not set — AI summaries will not work
#   ⚠ WiFi: HOME_WIFI not set — location detection disabled
#
# Summary: 5 OK, 2 warnings, 0 errors
```

A `--fix` flag can open the `.env` file in `$EDITOR` to resolve missing variables.

---

### 2.14 AI-generated daily summary on `wk daily finish`

**Current problem:** `wk daily finish` only writes the end time and time spent. The `Summary` section of the daily note is left blank, causing `wk daily audit` to flag every finalized note as `"missing summary"`. The `AIService` and `ClaudeCodeService` exist but are never called from `daily finish`.

**Design gap:** The existing `AIService.summarize` interface takes `daily_summaries: list[str]` (one summary per day) and a prompt built for weekly/period reports. This signature and prompt don't fit the single-day use case.

**Proposal:**

1. **Extend `AIService`** with a `summarize_day` method (or add a `period="daily"` path) that takes the day's tasks as input instead of a list of pre-written summaries:

```python
async def summarize_day(self, tasks: list[str], stats: dict | None = None) -> str: ...
```

2. **Implement in `ClaudeCodeService`** with a focused daily prompt — shorter than the weekly one, centred on "what was accomplished today", avoiding weekly-report sections like "Upcoming Focus" or "Strategic Decisions".

3. **Call from `finalize_daily_notes`** in `CommandManager`: parse the day's tasks (done, in-progress, blocked) from the note via `DailyParserService`, call `await ai_service.summarize_day(tasks)`, and write the result to the `Summary` section via `fix_summary`.

4. **Make it opt-out**, not opt-in — the summary is generated automatically on `wk daily finish` unless `--no-summary` is passed. If the AI service is unavailable (`claude` CLI not found, timeout), log a warning and leave the Summary blank rather than failing the command.

```bash
wk daily finish
# ✓ End time: 18:05
# ✓ Time spent: 08:12
# ✓ Summary generated by Claude Code
# Daily notes finalized.

wk daily finish --no-summary
# ✓ End time: 18:05
# ✓ Time spent: 08:12
# Daily notes finalized.
```

---

## Horizon 2B — Extended features

Features that extend and deepen the existing workflow.

### 2B.1 `wk standup`

Generate standup text automatically from yesterday's completed tasks and today's planned ones.

```bash
wk standup
# Yesterday: Fixed login timeout (PROJ-101), reviewed Maria's PR
# Today: Deploy hotfix, start Q3 planning
# Blockers: None

wk standup --post   # post directly to Slack
```

---

### 2B.2 `wk note`

Append a quick note to today's Notes section without opening the file. The text is a direct positional argument — no subcommand — to make it as fast as possible to capture a thought mid-work.

```bash
wk note "Discussed caching strategy with Alex — use Redis"
wk note "Prod deploy delayed to Thursday"
wk note "Discussed caching strategy with Alex — use Redis" --date 2026-06-29
```

The note is appended as a timestamped bullet in the Notes section of the daily file. If the file does not exist yet, it fails with a clear message rather than creating a partial file.

**Why positional over `wk note add "..."`:** one fewer word to type when you need to capture something quickly before losing the context. The subcommand form adds friction at exactly the wrong moment.

---

### 2B.3 `wk daily open`

Open today's daily note in `$EDITOR` directly.

```bash
wk daily open
wk daily open --date 2026-06-28
```

---

### 2B.4 `wk quarter report`

Generate a quarterly summary (Q1–Q4) analogous to the half-year report: total hours, tasks, epics, GitHub contributions, and an AI-generated summary.

```bash
wk quarter report
wk quarter report --quarter 2 --year 2026
```

**Template:** Create `templates/md/quarter.md` and `templates/txt/quarter.txt` — mirrors `month.md` at quarterly scale (Q1–Q4, 3-month date range, quarterly totals). Add `QUARTER_TEMPLATE` constant to `config.py`.

---

### 2B.5 `wk year report`

Annual summary: hours per month, tasks completed, epics contributed, GitHub contributions, streak record, and a full AI-generated narrative for the year.

```bash
wk year report
wk year report --year 2025
```

**Template:** Create `templates/md/year.md` and `templates/txt/year.txt` — mirrors `halfYear.md` at annual scale (12-month date range, annual totals, extended reflection questions). Add `YEAR_TEMPLATE` constant to `config.py`.

---

### 2B.6 `wk report compare`

Compare two periods side by side to detect workload trends.

```bash
wk report compare --period month   # this month vs last month
wk report compare --period quarter # Q2 vs Q1
wk report compare --from 2026-01 --to 2026-06
```

---

### 2B.7 `wk statistics completion`

Show daily task completion rate over time: how many tasks are planned vs completed each day, best/worst days, and weekly average.

```bash
wk statistics completion
# Average completion rate: 72%
# Best day: Friday (84%)
# Worst day: Monday (61%)
# Last 30 days: ████████░░ 72%
```

---

### 2B.8 `wk statistics workload`

Show hours worked per week over time. Detects overload patterns and prints a warning if multiple consecutive weeks exceed a configurable threshold (default 45h).

```bash
wk statistics workload
wk statistics workload --year 2026
# Week 23: 38h ████████░░
# Week 24: 41h ████████░░
# Week 25: 47h ██████████ ⚠ overload
```

---

### 2B.9 `wk statistics patterns`

Identify productivity patterns: best day of the week, most productive time of day, average tasks per day, carry-over rate (tasks that repeat across multiple days without being completed).

```bash
wk statistics patterns
# Most productive day: Thursday
# Average tasks completed/day: 4.2
# Carry-over rate: 28% of tasks repeat 2+ days
```

---

### 2B.10 Mood / energy tracking

Add an optional Energy field (1–5) to the daily notes. Surface it in reports to correlate workload with energy levels.

```bash
wk daily start
# ⚡ Energy today (1–5, Enter to skip): 4
```

Visible in `wk statistics workload` and month/quarter reports.

---

### 2B.11 Recurring tasks

Mark a task as recurring so it is automatically included every day (or on specific weekdays) without needing to carry it forward manually.

```bash
wk task recurring add "Check monitoring alerts" --every day
wk task recurring add "Update sprint board" --every monday,wednesday,friday
wk task recurring list
wk task recurring remove "Check monitoring alerts"
```

---

### 2B.12 Time tracking per task

Track time spent on individual tasks. `wk task start` / `wk task stop` log elapsed time against a task description or Jira key, and the data appears in daily and weekly reports.

```bash
wk task start PROJ-101
wk task stop
# PROJ-101: 1h 23m logged

wk task start "Write architecture doc"
wk task stop
```

---

### 2B.13 Jira bidirectional sync

When a task is marked as done in `wk`, optionally update its status in Jira automatically.

```bash
wk daily task done PROJ-101          # marks done locally
# Jira: PROJ-101 moved → Done ✓
```

Controlled by a config flag `JIRA_SYNC_ON_DONE=true` to avoid accidental updates.

---

### 2B.14 `wk pr review`

List open pull requests from your GitHub org that are waiting for your review, directly in the terminal.

```bash
wk pr review
# REPO-A  #142  Fix auth middleware         opened 2 days ago
# REPO-B  #98   Update API rate limits      opened 5 hours ago
```

---

### 2B.15 `wk backup schedule`

Set up an automated periodic backup using `launchd` (macOS) or `cron`.

```bash
wk backup schedule --every day --time 18:00
# LaunchAgent installed: backup runs daily at 18:00
wk backup schedule --disable
```

---

### 2B.16 Epic tags per daily note

Add a `Tags:` section at the end of each daily note listing the epic names of the Jira tasks worked on that day. This allows tracking approximately how many days were spent on each epic over time.

**Format** — last section of the daily note, after Summary:

```
Tags: Authentication Refactor, Platform Infra, Tech Debt
```

**How tags are populated:**

1. **`wk daily start`** — when Jira tasks are fetched, resolve each task's epic and write the `Tags:` line with the unique epic names. Tasks without a Jira key are ignored for tagging.
2. **`wk daily sync`** — refreshes the `Tags:` line if new tasks have been added or epics have changed during the day.
3. **Manual override** — the user can edit the `Tags:` line directly in the file at any time; `wk daily sync` does not overwrite manually added tags, it only adds missing ones.

**New commands enabled by this data:**

```bash
wk statistics tags
# Authentication Refactor    18 days
# Platform Infra             11 days
# Tech Debt                   6 days
# (untagged)                  4 days

wk statistics tags --year 2025

wk search --tag "Authentication Refactor"
# Lists all daily notes that include that epic tag
```

**Constraints:**
- Tags are stored in the file itself — no external database, consistent with the project's file-first philosophy.
- If `wk daily start` runs offline (`--offline`), the `Tags:` line is left empty and can be filled later with `wk daily sync`.
- Historical notes (created before this feature) will have no `Tags:` line; `wk daily audit` could report these as a coverage gap.

**Template change:** Add `**Tags:** {% if tags %}{{tags}}{% endif %}` before `{{extra}}` in `templates/md/dailyNotes.md` and `templates/txt/dailyNotes.txt`. `create_daily_notes()` passes `tags=""` until this feature is active.

---

### 2B.17 macOS Screen Time integration

Add an optional `App usage` section to the daily note and week report, populated from the macOS Screen Time database.

**Data source:** `~/Library/Application Support/Knowledge/knowledgeC.db` — a SQLite database macOS maintains with per-app usage records (bundle ID, start time, end time). Readable with stdlib `sqlite3`, no external API or dependency needed. Requires **Full Disk Access** granted by the user to the terminal app.

**Opt-in only:** controlled by `SCREEN_TIME_ENABLED=true` in `.env`. If not set, the feature is completely inactive and no section is added to the note.

**New service:** `ScreenTimeService(BaseService)` in `taskjournal/services/screen_time.py`:
- `get_usage(date) -> list[tuple[str, int]]` — returns `(app_name, seconds)` pairs for the given date, sorted by usage descending
- `health_check()` — verifies the DB exists and is readable
- Filters out system/noise apps (Finder, loginwindow, etc.) via a configurable blocklist

**Output in daily note** — appended automatically by `wk daily finish`:

```
## 🖥️ App usage
Cursor             4h 12m   ████████████░░░
Terminal           2h 45m   ████████░░░░░░░
Safari             1h 20m   ████░░░░░░░░░░░
Slack              0h 58m   ███░░░░░░░░░░░░
Zoom               0h 30m   █░░░░░░░░░░░░░░
```

**Output in week report** — aggregated totals per app across the 5 days, same bar format.

**Constraints:**
- macOS only — `health_check()` returns `UNCONFIGURED` on Linux/Windows with a clear message.
- The DB schema has changed between macOS versions; the service must handle `sqlite3.OperationalError` gracefully and fall back to an empty list with a warning.
- App names are derived from bundle IDs (e.g. `com.apple.dt.Xcode` → `Xcode`) via a lookup table; unknown bundles show the last component of the bundle ID.
- macOS 15 (Sequoia) moved some Screen Time data — the service should try both the legacy and new paths.

**Template changes:** Add `{% if app_usage %}## 🖥️ App usage\n\n{{app_usage}}\n{% endif %}` before `{{extra}}` in `dailyNotes.md/.txt`, and after the summary block in `weekSummary.md/.txt`. `create_daily_notes()` and `create_week_summary()` pass `app_usage=""` until this feature is active — the section is hidden by the `{% if %}`.

---

### 2B.18 `wk feedback` — capture received and given feedback

A dedicated command for logging professional feedback throughout the year, so performance reviews and half-year reports have specific, dated evidence to draw from.

**Storage:** `BASE_DIR/{year}/feedback/feedback.md` — one file per year, appended chronologically. Same file-first philosophy as the rest of the project.

```bash
# Log feedback received
wk feedback received "Your auth PR review caught a subtle race condition — very thorough" --from "Maria" --context "PR #142"

# Log feedback given
wk feedback given "Great ownership of the Friday incident, well communicated" --to "Alex" --context "1:1"

# List all feedback
wk feedback list
wk feedback list --quarter 2
wk feedback list --from "Maria"
wk feedback list --type received   # or: given
```

**File format:**

```markdown
## 2026-06-30

### Received
- **From:** Maria · **Context:** PR #142
  > "Your auth PR review caught a subtle race condition — very thorough"

### Given
- **To:** Alex · **Context:** 1:1
  > "Great ownership of the Friday incident, well communicated"
```

**AI integration:** the half-year and year report AI summaries (`create_half_year_report`, `create_year_report`) should read the feedback file and include it as context for the "Collaboration & Mentoring" section, giving the AI real evidence instead of inferring it from task descriptions.

**New service:** `FeedbackService(BaseService)` in `taskjournal/services/feedback.py`:
- `add_received(text, from_person, context, date)` — appends a received entry
- `add_given(text, to_person, context, date)` — appends a given entry
- `list_feedback(quarter, year, person, feedback_type)` — returns filtered entries
- `get_for_period(start, end)` — used by report generation

**Why separate from 1on1 files:** 1on1 files capture meeting agendas and action items; feedback entries are point-in-time observations that span all contexts (code reviews, Slack, hallway conversations, team meetings). Keeping them separate makes them easier to query at review time.

**Template changes:**
- Create `templates/md/feedback.md` and `templates/txt/feedback.txt` — entry block format (date header, received/given sections with from/to, context, quoted text). Add `FEEDBACK_TEMPLATE` constant to `config.py`.
- In `templates/md/halfYear.md` and `.txt`: replace the static "6. Feedback" section (empty bullet points `- **Received Feedback:**` / `- **Given Feedback:**`) with `{{feedback}}`. `create_half_year_review()` passes `feedback=""` until this feature is active.

---

## Horizon 3 — Long-term ideas

Broader ideas that require more planning or depend on new infrastructure.

### 3.1 `wk export`

Export notes or reports to HTML or PDF to share with managers or for archiving.

```bash
wk export week --format html --date 2026-06-23
wk export month --format pdf
```

---

### 3.2 Interactive TUI dashboard

An interactive panel (with `textual` or advanced `rich`) showing in real time: day time, pending tasks, streak, upcoming holidays, and Jira integration.

```bash
wk dashboard
```

---

### 3.3 Multi-team / multi-project support

Allow having multiple configuration profiles (one per client, one per internal project) and switching between them easily.

```bash
wk --profile client-a daily start
wk --profile internal week report
```

---

### 3.4 Calendar sync

Read the calendar (Google Calendar / Outlook via API) to automatically populate the day's meetings in the notes section.

---

### 3.6 Slack summary

Pull a summary of Slack activity (mentions, threads, DMs) for the day and include it in the daily notes or week report. Useful for capturing context that lives in Slack but never makes it into the journal.

Possible entry points:
- `wk daily slack` — fetch today's Slack highlights and append them to the current daily note
- Automatic inclusion on `wk daily start` if the Slack integration is configured

Requires a Slack app with `channels:history`, `im:history`, and `users:read` OAuth scopes.

---

## Horizon F — Fun & Easter eggs

Small, self-contained features with no business impact — just enjoyable to use.

### F.1 Marquee on `wk daily start`

After creating the daily note, display a short animated scrolling text (Rich `Live`) with a welcome message and the day/week info. Disappears automatically after ~3 seconds (`transient=True` so it leaves no trace in the terminal).

```
   Good morning! Week 27 · Tuesday 2026-06-30 · Let's make it count 🚀   
```

**Implementation:** create `taskjournal/cli/animations.py` with a shared `run_marquee(text, style, duration)` utility. Call it at the end of `daily_start` in `cli/commands/daily.py`.

---

### F.2 Marquee on `wk daily finish`

After finalizing the day, display a celebratory scrolling message before returning to the prompt.

```
   Day complete · Tuesday 2026-06-30 · Great work today! 🎉   
```

**Implementation:** reuse `run_marquee` from `animations.py`. Call it at the end of `daily_finish` in `cli/commands/daily.py`, style `bold magenta`, duration 3.5s.

---

### F.3 Ticker on `wk info show`

After the info table, scroll a one-liner ticker with the week number, day name, and app version. Subtler than the daily marquees — dim style, 2.5s.

```
   📅 Week 27 · Tuesday, 30 June 2026 · wk v0.47.0   
```

**Implementation:** reuse `run_marquee` from `animations.py`. Append to the `show` command in `cli/commands/info.py`.

---

### F.4 `wk joke`

Fetch and display a random joke from `https://v2.jokeapi.dev/joke/Any?safe-mode&blacklistFlags=nsfw,racist,sexist,explicit` (English, all safe categories). For two-part jokes, show the setup first, pause ~1.5s with a Rich `Spinner`, then reveal the punchline.

```bash
wk joke
╭─────────────────────────────────────────────────╮
│ 🎭  Why do programmers prefer dark mode?        │
│                                                 │
│     ⠋  ...                                      │
│                                                 │
│     Because light attracts bugs!                │
╰─────────────────────────────────────────────────╯
```

Fallback: if the API is unreachable (timeout 5s), pick from a local hardcoded list of 8–10 jokes so it works offline too.

**Implementation:** new file `taskjournal/cli/commands/fun.py` with a single `build_app()` following the `search.py` callback pattern. Uses `httpx.get()` (sync) — no new service needed. Register in `cli/cli.py` as `wk joke` under `🗂️ Tools`.

---

## Priority Summary

| ID | Improvement / Feature | Complexity | Value |
|---|---|---|---|
| 1.1 | Robust parser (sections as constants) | Low | High |
| 1.4 | Complete task statuses | Low | High |
| 1.5 | "Legacy" ID in parser | Low | Medium |
| 1.8 | Previous-day completion check on `wk daily start` | Low | High |
| 1.9 | Incomplete-day warnings in `wk week report` | Low | High |
| 1.10 | Smarter task deduplication on carry-forward | Low | High |
| 1.11 | CLI command reorganisation (extract task, merge report, fix panels) | Medium | High |
| 1.12 | Split `CommandManager` into domain-specific classes | Medium | High |
| 1.13 | Parser returns `ParsedNote` model instead of raw `dict` | Low | Medium |
| 1.14 | Unify async model — establish clear sync/async boundary | Medium | Medium |
| 1.15 | Register `HolidayService` in DI container | Low | Medium |
| 1.17 | Full `.txt` format support — fix all hardcoded `.md` refs + test coverage | Medium | High |
| 1.18 | Template review — fix broken `.txt`, sync all formats, new templates for planned features | Medium | High |
| 1.19 | Separate user output from logger — replace `logger.info()` with `console.print()` | Low | High |
| 2.6 | Explicit offline mode | Low | High |
| 2.1 | `wk daily status` | Low | High |
| 2.9 | `wk daily audit` | Low | High |
| 2.10 | macOS alarm on `wk daily start` | Low | High |
| 2.11 | `wk daily sync` (Jira tasks) | Medium | High |
| 2.13 | `wk doctor` | Low | High |
| 1.7 | Improve `wk info` | Low | Medium |
| 2.8 | `wk daily check` | Low | Medium |
| 1.2 | Migrate templates to Jinja2 | Medium | Medium |
| 1.3 | GithubService context manager | Medium | Medium |
| 2.2 | `wk daily task add/done` | Medium | High |
| 2.7 | `wk week list` | Low | Medium |
| 2.5 | `wk 1on1 add-topic` | Low | Medium |
| 2.14 | AI-generated daily summary on `wk daily finish` | Medium | High |
| 2.3 | `wk search` | Medium | High |
| 2.4 | `wk statistics streak` | Low | Low |
| 1.6 | AI service abstraction | High | Medium |
| 2B.1 | `wk standup` | Low | High |
| 2B.2 | `wk note <text>` — quick capture posicional, sense subcomanda | Low | High |
| 2B.3 | `wk daily open` | Low | Medium |
| 2B.4 | `wk quarter report` | Medium | High |
| 2B.5 | `wk year report` | Medium | High |
| 2B.6 | `wk report compare` | Medium | Medium |
| 2B.7 | `wk statistics completion` | Low | High |
| 2B.8 | `wk statistics workload` | Low | High |
| 2B.9 | `wk statistics patterns` | Medium | Medium |
| 2B.10 | Mood / energy tracking | Low | Medium |
| 2B.11 | Recurring tasks | Medium | High |
| 2B.12 | Time tracking per task | High | High |
| 2B.13 | Jira bidirectional sync | Medium | Medium |
| 2B.14 | `wk pr review` | Low | Medium |
| 2B.15 | `wk backup schedule` | Medium | Low |
| 2B.16 | Epic tags per daily note + `wk statistics tags` | Medium | High |
| 2B.17 | macOS Screen Time integration — app usage in daily + week report | Medium | High |
| 2B.18 | `wk feedback received/given` — capture feedback for performance reviews | Low | High |
| 3.1 | `wk export` | High | Medium |
| 3.2 | TUI dashboard | High | High |
| 3.3 | Multi-profile | High | Low |
| 3.4 | Calendar sync | Very High | Low |
| 3.6 | Slack summary | High | Medium |
| F.1 | Marquee on `wk daily start` | Low | Fun |
| F.2 | Marquee on `wk daily finish` | Low | Fun |
| F.3 | Ticker on `wk info show` | Low | Fun |
| F.4 | `wk joke` — fetch random joke with setup/punchline | Low | Fun |
