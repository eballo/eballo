# Changelog

## 0.58.0

- PR review + ascii title

## 0.57.0

- improve wk info

## 0.56.0

- abstraction

## 0.55.0

- consistency

## 0.54.0

- user output improvements no logger info

## 0.53.0

- template review

## 0.52.0

- txt format support

## 0.51.0

- unify async model

## 0.50.0

- typed parser models

## 0.49.0

- Split CommandManager into domain-specific classes (1.12)

## 0.48.0

- 1.11 CLI command reorganisation — wk task, wk report, panels

## 0.47.0

- Remove manual changelog entry — CI adds it automatically on merge

## 0.46.0

- Add Claude Code CLI as AI provider with multi-provider selection

## 0.45.0

- Version 0 44 0

## 0.44.0

- Fix CI bump workflow: YAML literal block parse error caused by unindented `--notes` content
- Use `printf` + `--notes-file` to safely pass multi-line release notes

## 0.43.0

## 0.42.0

- Fix CI bump workflow: use annotated tags so `--follow-tags` pushes them to the remote
- Add GitHub Release creation step to bump workflow

## 0.41.0

- Update changelog format and fix stale 0.40.0 entry

## 0.40.0

- Fix `write_env` to preserve extra user-defined keys in `.env` (no data loss on re-write)
- Fix `create_one_on_one` to create parent directory before writing the file
- Fix task deduplication: keyless task now replaced by a matching keyed Jira task
- Fix `daily_status` / `daily_check` to not create week folder unnecessarily (use `resolve_daily_notes_file`)
- Fix WiFi placeholder constants unified in `constants.py` (`PLACEHOLDER_HOME_WIFI`, `PLACEHOLDER_OFFICE_WIFI`)
- Fix Jira service gracefully skips connection when token is unconfigured
- Fix backup service to accept `Path` objects in addition to `str`
- Fix `get_previous_day_issues` to walk up to 14 calendar days back to find last existing note
- Register `SetupService` in DI container — `wk setup` no longer bypasses DI
- Fix CI bump workflow for Poetry→uv migration (`[project]` table) and `wiki/` → `docs/` path
- Add GitHub Release creation step to bump workflow

## 0.38.0

- Migrate from Poetry to uv
- Unify wiki/ and docs/ directories
- Translate all docs to English
- Fix .bumpversion.cfg out-of-sync version
- Fix sample.env missing variables (BACKUP_DIR, OPENAI_API_KEY, HOME_WIFI, OFFICE_WIFI)
- Fix pre-commit hook versions and pytest path
- Fix sonar-project.properties python version and coverage path
- Remove redundant pytest.ini (consolidated into pyproject.toml)
- Add `wk setup` interactive configuration wizard
- Refactor services: extract duplicated code (`seconds_to_hours_minutes`, `_classify_work_location`, `_process_daily_file`)
- Inject all credentials/settings via DI container (no module-level config imports in services)
- Replace all legacy `typing.List/Optional/Dict` with Python 3.12 built-in types
- Replace all bare `import os/re/uuid` with specific imports (`from os.path import join`, etc.)
- Create `CLAUDE.md` with project coding guidelines
- Create `BaseService` health check contract for all services
- Add `wk doctor` health check command
- Add `wk daily status` — current day elapsed time, task breakdown and finalization state
- Add `wk daily check` — validate structure of today's daily notes
- Add `wk daily audit` — scan all notes for a year and report incomplete ones (`--fix` interactive CLI to fix missing fields)
- Warn if previous day's note is incomplete before creating today's note, with option to fix interactively
- Warn if any daily note is incomplete before generating week report
- Smarter task deduplication (normalize descriptions + match on Jira key)
- Fix parser to generate proper `uuid4()` for legacy task IDs
- Parser section detection uses centralised regex constants — no more false positives from content lines
- Complete task statuses — `[>]` IN_PROGRESS and `[~]` CODE_REVIEW in parser and formatter
- Add `wk daily start --offline` flag — skips all Jira and GitHub API calls
- Add `wk week list` — shows daily notes status and time for a given week
- Add `wk daily task add/done/block/list` — manage tasks from CLI without opening the file
- Add `wk search` — search keyword across all notes with `--from`, `--to`, `--type` filters
- `wk info show` — now shows BASE_DIR, template format and integration health status
- Add `wk 1on1 add-topic` — append a topic to the next 1on1 file from the CLI
- Add `wk statistics streak` — consecutive journaling streak and all-time record
- Add `wk daily sync` — pull Jira tasks and add missing ones to current day's notes
- Replace `**Lunch:**` field with `**Break:**` — supports multiple break lines per day (`**Break:** 01:00 lunch`, `**Break:** 00:15 morning`); old files without `Break:` are backward-compatible
- Add `wk daily task wip` — mark a task as work in progress (`[>]`)
- Task commands (`add`, `done`, `block`, `wip`) now use positional arguments instead of `--desc`
- `wk daily task list` now shows a status column with colored badges and styled descriptions
- Add `wk holidays add <date> <description>` — append a holiday to the holidays file under a given category
- Add `wk fireman` command group: `add`, `list`, `upcoming`, `summary`

## 0.37.0

- #110 Group commands wk output

## 0.36.0

- #108 transform all code into classes

## 0.35.0

- #98 Improve code

## 0.34.0

- #80 - add Depenency Injection

## 0.33.0

- #95 update readme

## 0.32.0

- #93 Improve month command

## 0.31.0

- #91 Improve week command

## 0.30.0

- #87 Improve Holidays command

## 0.29.0

- #87 Fix total time spent calculation

## 0.28.0

- fix jira issue - pagination

## 0.27.0

- Fix some sonar issues

## 0.26.0

- Add Mypy + fix issues

## 0.25.0

- Improve code coverage

## 0.24.0

- #75 Small improvements test

## 0.23.0

Improve JiraService + code coverage

## 0.22.0

- Improve Readme

## 0.21.0

- Add fireman weeks

## 0.20.0

- Improve get location from wifi service

## 0.19.0

- be able to get the pending tasks from previous week

## 0.18.0

- add statistics command

## 0.17.0

- add 1on1 report

## 0.16.0

- add holidays populate command

## 0.15.0

- add holidays command to manage holidays

## 0.14.0

- add migrate command to help migrate from older versions

## 0.13.0

- Add github URL to the Code Review section
- Validate if the PR was already reviewd

## 0.12.1

- Improve bump version to support (fix/major/minor versions)
- add changelog section

## 0.12.0

- add Jira link
- addd github repo link

## 0.11.0

- add work location
- add firefighter mode
- add use of jinja2 library

## 0.9.0

- Improve Github Service
    - Improve logging if it doesn't exist
    - migrate to async library
- update services + tests to use async calls

## 0.8.0

- Improve Jira Service
    - Improve logging if it doesn't exist
    - migrate to version 3 jsql
    - migrate to httpx to use async calls
- update services to use async calls

## 0.7.0

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
