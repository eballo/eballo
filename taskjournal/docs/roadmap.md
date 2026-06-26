# Task Journal — Roadmap

> Based on analysis of the current codebase (v0.37.0). Organised into three horizons: foundational technical improvements, new features, and long-term ideas.

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

### 3.5 Claude Code integration

Expose `wk` context to Claude Code so the AI assistant can read the current day's note, query pending tasks, and help write or update journal entries directly from the editor.

Possible entry points:
- An MCP server (`wk mcp`) that exposes tools such as `get_today`, `list_pending_tasks`, `add_task`, and `finish_day`.
- A `CLAUDE.md` snippet that instructs Claude Code how to interact with `wk` commands during a coding session.
- A `wk daily summarise` command that sends the day's raw notes to Claude and appends an AI-generated summary section.

```bash
wk mcp          # start the MCP server for Claude Code
wk daily summarise   # AI-generated end-of-day summary via Claude
```

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
| 2.3 | `wk search` | Medium | High |
| 2.4 | `wk statistics streak` | Low | Low |
| 1.6 | AI service abstraction | High | Medium |
| 3.1 | `wk export` | High | Medium |
| 3.2 | TUI dashboard | High | High |
| 3.5 | Claude Code integration (MCP server) | High | High |
| 3.3 | Multi-profile | High | Low |
| 3.4 | Calendar sync | Very High | Low |
