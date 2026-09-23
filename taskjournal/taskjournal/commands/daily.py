from datetime import datetime, timedelta, time as time_t
from os import makedirs, listdir, getuid
from os.path import basename, dirname, exists, expanduser, join
from pathlib import Path
from re import match as re_match
from subprocess import run as subprocess_run
from sys import platform

from jinja2 import Template

from taskjournal.config import (
    DAILY_NOTES_TEMPLATE,
    BASE_DIR,
)
from taskjournal.constants import SECTION_SUMMARY
from taskjournal.models.task import Task, Status
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.ai.base import AIService
from taskjournal.services.daily_audit import DailyAuditService
from taskjournal.services.daily_sync import DailySyncService
from taskjournal.services.daily_statistics import DailyStatisticsService
from taskjournal.services.file import FileService
from taskjournal.services.calendar.fireman import FiremanService
from taskjournal.services.integrations.github import GithubService
from taskjournal.services.integrations.jira import JiraService
from taskjournal.services.logger import console, logger
from taskjournal.services.parser import DailyParserService
from taskjournal.services.recurring import RecurringTasksService
from taskjournal.services.task_manager import TaskManager
from taskjournal.services.time import TimeService
from taskjournal.services.utils import FormatUtils

_LAUNCH_AGENTS_DIR = expanduser("~/Library/LaunchAgents")  # for backward-compat cancel of old launchd alarms
_APPLESCRIPT_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


class DailyCommands:

    def __init__(
        self,
        jira: JiraService,
        github: GithubService,
        task_formatter: TaskFormatter,
        parser: DailyParserService,
        task_manager: TaskManager,
        file_service: FileService,
        time_service: TimeService,
        ai_service: AIService,
        recurring_service: RecurringTasksService | None = None,
        daily_alarms_enabled: bool = True,
        debug: bool = False,
        audit_service: DailyAuditService | None = None,
        sync_service: DailySyncService | None = None,
        statistics_service: DailyStatisticsService | None = None,
    ) -> None:
        self.debug = debug
        self._alarms_enabled = daily_alarms_enabled
        self.jira = jira
        self.github = github
        self.task_formatter = task_formatter
        self.parser = parser
        self.task_manager = task_manager
        self.file_service = file_service
        self.time_service = time_service
        self.ai_service = ai_service
        self._recurring = recurring_service or RecurringTasksService()
        self._audit = audit_service or DailyAuditService(file_service, time_service, parser)
        self._sync = sync_service or DailySyncService(jira, github, task_formatter, file_service, parser)
        self._statistics = statistics_service or DailyStatisticsService(parser, self._audit)

    def _get_week_folder(self, date: datetime) -> str:
        week_folder = self.file_service.get_week_folder(BASE_DIR, date)
        makedirs(week_folder, exist_ok=True)
        return week_folder

    def _get_daily_notes_file_path(self, today: datetime) -> str:
        week_folder = self._get_week_folder(today)
        daily_notes_name = self.time_service.get_daily_notes_name(today)
        return join(week_folder, daily_notes_name)

    def _note_issues(self, file_path: str) -> list[str]:
        return self._audit.note_issues(file_path)

    def audit_daily_notes(self, year: int) -> list[tuple[str, str, list[str]]]:
        return self._audit.audit_daily_notes(year)

    def count_week_folders(self, year: int) -> int:
        return self._audit.count_week_folders(year)

    def audit_weekly_coverage(self, year: int) -> list[tuple[str, list[str]]]:
        return self._audit.audit_weekly_coverage(year)

    def get_previous_day_issues(self, today: datetime) -> tuple[str, str, list[str]] | None:
        return self._audit.get_previous_day_issues(today, self._get_daily_notes_file_path)

    def _warn_incomplete_week_notes(self, week_date: datetime, week_folder: str) -> None:
        self._audit.warn_incomplete_week_notes(week_date, week_folder)

    def get_streak_stats(self, today: datetime) -> dict[str, object]:
        return self._statistics.get_streak_stats(today)

    async def create_daily_notes(
        self,
        create_datetime: datetime,
        force: bool = False,
        firefighter: bool = False,
        work_from: str | None = None,
        offline: bool = False,
        energy: int | None = None,
    ) -> None:
        daily_notes_file = self._get_daily_notes_file_path(create_datetime)
        template_content = self.file_service.load_template(DAILY_NOTES_TEMPLATE)

        if exists(daily_notes_file) and not force:
            logger.warning(f"Daily notes file already exists: {daily_notes_file}")
            return None

        if create_datetime.weekday() >= 5:
            day_name = create_datetime.strftime("%A")
            logger.warning(f"Creating a daily note on a {day_name} — are you sure?")

        if offline:
            logger.warning("Offline mode — skipping Jira and GitHub calls.")
            sprint_name = "Offline mode"
            pending: list[Task] = []
            code_review: list[Task] = []
        else:
            sprint = self.jira.get_active_sprint()
            sprint_name = sprint.name if sprint else "No active sprint"
            pending = await self.jira.get_current_sprint_tasks_not_done_assigned_to_me()
            code_review = await self.jira.get_current_sprint_tasks_in_code_review()
            async with self.github:
                await self.github.update_status_if_task_reviewed(code_review)

        folder_path = dirname(daily_notes_file)
        current_file = basename(daily_notes_file)
        work_from = work_from if work_from else self.task_manager.get_work_from_location(create_datetime)

        is_fireman_week = FiremanService(create_datetime).is_fireman_week()
        firefighter = firefighter if firefighter else is_fireman_week

        default = self.task_manager.get_default_tasks()
        if create_datetime.strftime("%A") == "Monday":
            logger.debug("Checking for pending tasks from last week...")
            one_week_ago = create_datetime - timedelta(weeks=1)
            week_folder = self._get_week_folder(one_week_ago)
            last_week_pending_tasks = self.task_manager.get_previous_pending_tasks(week_folder, current_file)
        else:
            last_week_pending_tasks = []

        previous_pending_tasks = self.task_manager.get_previous_pending_tasks(folder_path, current_file)
        recurring_descs = self._recurring.get_for_day(create_datetime)
        recurring_tasks = [TaskManager.create_task(d) for d in recurring_descs]

        # Jira's "not done" query returns tickets regardless of when work on them
        # started, so a still-TODO ticket already seen in yesterday's notes reads as
        # carry-over, not new work — sink it below today's fresh/active tasks instead
        # of letting it show up first.
        carried_keys = {
            key for t in previous_pending_tasks + last_week_pending_tasks if (key := getattr(t, "key", None))
        }
        fresh_pending = [
            t for t in pending if getattr(t, "status", None) != Status.TODO or getattr(t, "key", None) not in carried_keys
        ]
        carried_pending = [
            t for t in pending if getattr(t, "status", None) == Status.TODO and getattr(t, "key", None) in carried_keys
        ]

        # Recurring checklist items lead the list, followed by all Jira-sourced
        # tasks (fresh/active ones first, then carry-over) — see comment above.
        tasks = TaskManager.unique_tasks(
            default + recurring_tasks + fresh_pending + carried_pending + last_week_pending_tasks + previous_pending_tasks
        )

        all_tasks = tasks + code_review
        epic_names = TaskManager.get_unique_epic_names(all_tasks)
        tags_line = f"Tags: {', '.join(epic_names)}" if epic_names else ""

        break_h, break_m = TimeService.seconds_to_hours_minutes(
            TimeService.get_expected_break_seconds(create_datetime)
        )
        daily_notes_content = Template(template_content).render(
            day_name=create_datetime.strftime("%A"),
            date=create_datetime.strftime("%Y-%m-%d"),
            start_time=create_datetime.strftime("%H:%M:%S"),
            end_time="",
            break_time=f"{break_h:02d}:{break_m:02d}",
            time_spent="",
            work_from=work_from,
            sprint_name=sprint_name,
            tasks=self.task_formatter.format_tasks(tasks, with_name=True),
            code_review_tasks=self.task_formatter.format_tasks(code_review, with_name=True),
            notes="-",
            summary="",
            firefighter=firefighter,
            firefighter_notes="-",
            energy=energy,
            extra=tags_line,
        )

        self.file_service.write_to_file(daily_notes_file, daily_notes_content)

        week_folder = self._get_week_folder(create_datetime)
        accumulated_seconds = self.time_service.get_accumulated_week_seconds(week_folder, create_datetime)
        days_before_today = min(create_datetime.weekday(), 5)
        expected_seconds = TimeService.get_expected_week_seconds_before(week_folder, create_datetime)
        extra_seconds = accumulated_seconds - expected_seconds
        today_seconds = TimeService.get_expected_workday_seconds(create_datetime)
        today_work_seconds = min(today_seconds, max(0, today_seconds - extra_seconds))
        break_seconds = TimeService.get_expected_break_seconds(create_datetime)
        finish = self.time_service.estimated_finish_time(create_datetime, week_folder, accumulated_seconds)

        accumulated_h, accumulated_m = TimeService.seconds_to_hours_minutes(accumulated_seconds)
        expected_h, expected_m = TimeService.seconds_to_hours_minutes(expected_seconds)
        extra_sign = "+" if extra_seconds >= 0 else "-"
        extra_h, extra_m = TimeService.seconds_to_hours_minutes(abs(extra_seconds))
        today_h, today_m = TimeService.seconds_to_hours_minutes(today_work_seconds)

        logger.debug(f"Daily Notes created successfully {daily_notes_file}")
        day_number = min(days_before_today + 1, 5)
        console.print(
            f"Day {day_number} of 5"
            f"  |  accumulated: {accumulated_h}h {accumulated_m:02d}m"
            f"  |  expected: {expected_h}h {expected_m:02d}m"
            f"  |  extra: {extra_sign}{extra_h}h {extra_m:02d}m"
        )
        streak = self.get_streak_stats(create_datetime)
        console.print(f"Streak: {streak['current']} day(s)  |  all-time best: {streak['longest']} day(s)")
        break_label = f"{break_h}h {break_m:02d}m break" if break_seconds else "no break"
        console.print(
            f"Today: {today_h}h {today_m:02d}m work + {break_label}"
            f"  →  estimated finish {finish.strftime('%H:%M')}"
        )
        if self._alarms_enabled:
            date_str = create_datetime.strftime("%Y-%m-%d")
            calm_time = finish - timedelta(minutes=30)
            calm_file = join(week_folder, f".alarm_job_{date_str}_{calm_time.strftime('%H%M')}")
            finish_file = join(week_folder, f".alarm_job_{date_str}_{finish.strftime('%H%M')}")
            self._schedule_macos_alarm(calm_time, calm_file, "It is time to calm down")
            self._schedule_macos_alarm(finish, finish_file, "Time to wrap up!")
        return None

    def _schedule_macos_alarm(
        self, finish_time: datetime, alarm_file: str, message: str = "Time to wrap up!"
    ) -> None:
        if platform != "darwin":
            return
        finish_str = finish_time.strftime("%H:%M")
        date_str = finish_time.strftime("%Y-%m-%d")
        tag = f"wk:{date_str}:{finish_str}"
        seconds = finish_time.hour * 3600 + finish_time.minute * 60
        month_name = _APPLESCRIPT_MONTHS[finish_time.month - 1]
        script = (
            f'tell application "Reminders"\n'
            f'    set theDate to current date\n'
            f'    set year of theDate to {finish_time.year}\n'
            f'    set day of theDate to 1\n'
            f'    set month of theDate to {month_name}\n'
            f'    set day of theDate to {finish_time.day}\n'
            f'    set time of theDate to {seconds}\n'
            f'    make new reminder at end of default list'
            f' with properties {{name:"{message}", body:"{tag}", due date:theDate}}\n'
            f'end tell'
        )
        try:
            result = subprocess_run(["osascript", "-e", script], capture_output=True, timeout=10)
            if result.returncode == 0:
                Path(alarm_file).write_text(f"reminder|{date_str}|{finish_str}|{message}")
                day_label = finish_time.strftime("%a %d %b")
                console.print(f"[dim]Alarm set for {day_label} at {finish_str} — {message}[/dim]")
            else:
                logger.debug(f"Could not create reminder: {result.stderr.decode().strip()}")
        except Exception as e:
            logger.debug(f"Could not schedule alarm: {e}")

    def _cancel_macos_alarm(self, alarm_file: str) -> None:
        if platform != "darwin":
            return
        alarm_path = Path(alarm_file)
        if not alarm_path.exists():
            return
        try:
            content = alarm_path.read_text().strip()
            if content.startswith("reminder|"):
                parts = content.split("|", 3)
                second = parts[1] if len(parts) > 1 else ""
                # New format: reminder|YYYY-MM-DD|HH:MM|message  (tag = wk:date:HH:MM)
                # Old format: reminder|wk — ... (name-based)
                if re_match(r"\d{4}-\d{2}-\d{2}", second):
                    time_part = parts[2] if len(parts) > 2 else ""
                    tag = f"wk:{second}:{time_part}"
                    script = (
                        f'tell application "Reminders"\n'
                        f'    set toDelete to (every reminder whose body is "{tag}")\n'
                        f'    repeat with r in toDelete\n'
                        f'        delete r\n'
                        f'    end repeat\n'
                        f'end tell'
                    )
                else:
                    script = (
                        f'tell application "Reminders"\n'
                        f'    set toDelete to (every reminder whose name is "{second}")\n'
                        f'    repeat with r in toDelete\n'
                        f'        delete r\n'
                        f'    end repeat\n'
                        f'end tell'
                    )
                subprocess_run(["osascript", "-e", script], capture_output=True, timeout=10)
            elif "|" in content:
                label = content.split("|")[0]
                plist_path = join(_LAUNCH_AGENTS_DIR, f"{label}.plist")
                subprocess_run(["launchctl", "bootout", f"gui/{getuid()}", label], capture_output=True)
                Path(plist_path).unlink(missing_ok=True)
            else:
                subprocess_run(["kill", content.split(":")[0]], capture_output=True)
            alarm_path.unlink()
            console.print("[dim]Alarm cancelled[/dim]")
        except Exception as e:
            logger.debug(f"Could not cancel alarm: {e}")

    def _pending_wk_tags(self) -> set[str]:
        script = (
            'tell application "Reminders"\n'
            '    set bs to {}\n'
            '    repeat with r in (every reminder whose completed is false)\n'
            '        set b to body of r\n'
            '        if b starts with "wk:" then set end of bs to b\n'
            '    end repeat\n'
            '    return bs\n'
            'end tell'
        )
        try:
            result = subprocess_run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0 or not result.stdout.strip():
                return set()
            return {t.strip() for t in result.stdout.strip().split(",")}
        except Exception:
            return set()

    def list_alarms(self, weeks_back: int = 4) -> list[dict[str, object]]:
        now = datetime.now()
        pending_tags = self._pending_wk_tags()
        results: list[dict[str, object]] = []
        seen: set[str] = set()
        for offset in range(weeks_back + 1):
            day = now - timedelta(weeks=offset)
            folder = self.file_service.get_week_folder(BASE_DIR, day)
            try:
                for fname in sorted(listdir(folder)):
                    if not fname.startswith(".alarm_job_"):
                        continue
                    date_str = fname[len(".alarm_job_"):len(".alarm_job_") + 10]
                    if fname in seen:
                        continue
                    seen.add(fname)
                    try:
                        content = Path(join(folder, fname)).read_text().strip()
                    except OSError:
                        continue
                    scheduled_time: str | None
                    message: str | None = None
                    if content.startswith("reminder|"):
                        parts = content.split("|", 3)
                        second = parts[1] if len(parts) > 1 else ""
                        if re_match(r"\d{4}-\d{2}-\d{2}", second):
                            job_id = second
                            scheduled_time = parts[2] if len(parts) > 2 else None
                            message = parts[3] if len(parts) > 3 else None
                            tag = f"wk:{job_id}:{scheduled_time}" if scheduled_time else f"wk:{job_id}"
                            is_alive = tag in pending_tags
                        else:
                            job_id = second
                            scheduled_time = parts[2] if len(parts) > 2 else None
                            is_alive = job_id in {t.replace("wk:", "") for t in pending_tags}
                    elif "|" in content:
                        job_id, scheduled_time = content.split("|", 1)
                        is_alive = subprocess_run(
                            ["launchctl", "list", job_id], capture_output=True, timeout=5
                        ).returncode == 0
                    else:
                        parts_c = content.split(":", 1)
                        job_id = parts_c[0]
                        scheduled_time = parts_c[1] if len(parts_c) > 1 else None
                        is_alive = subprocess_run(
                            ["kill", "-0", job_id], capture_output=True
                        ).returncode == 0
                    try:
                        is_past = datetime.strptime(date_str, "%Y-%m-%d").date() < now.date()
                    except ValueError:
                        is_past = False
                    results.append({
                        "date": date_str,
                        "job_id": job_id,
                        "scheduled": scheduled_time,
                        "message": message,
                        "is_past": is_past,
                        "is_alive": is_alive,
                    })
            except (FileNotFoundError, OSError):
                pass
        results.sort(key=lambda x: str(x["date"]))
        return results

    def set_alarm(
        self, date: datetime, alarm_time: datetime, message: str = "Time to wrap up!"
    ) -> None:
        time_suffix = alarm_time.strftime("%H%M")
        alarm_file = join(
            self._get_week_folder(date),
            f".alarm_job_{date.strftime('%Y-%m-%d')}_{time_suffix}",
        )
        if Path(alarm_file).exists():
            self._cancel_macos_alarm(alarm_file)
        self._schedule_macos_alarm(alarm_time, alarm_file, message)

    def cancel_alarm_for_date(self, date: datetime) -> bool:
        folder = self.file_service.get_week_folder(BASE_DIR, date)
        prefix = f".alarm_job_{date.strftime('%Y-%m-%d')}"
        found = False
        try:
            for fname in listdir(folder):
                if fname.startswith(prefix):
                    self._cancel_macos_alarm(join(folder, fname))
                    found = True
        except (FileNotFoundError, OSError):
            pass
        return found

    async def finalize_daily_notes(self, custom_date: datetime, no_summary: bool = False, force: bool = False) -> None:
        daily_notes_file = self._get_daily_notes_file_path(custom_date)

        if not exists(daily_notes_file):
            logger.error(f"Daily notes file does not exist: {daily_notes_file}")
            return None

        if not force and self.file_service.check_finalized_in_file(daily_notes_file):
            logger.warning(f"File '{daily_notes_file}' is already finalized.")
            return None

        try:
            await self.sync_daily_notes(custom_date)
        except Exception as e:
            logger.warning(f"Code review sync failed: {e}")

        if not custom_date:
            final_time = datetime.now()
        else:
            logger.warning(f"FORCE DATE - Custom date provided: {custom_date}")
            final_time = custom_date

        content = self.file_service.get_lines(daily_notes_file)
        created_line_index, created_time = self.time_service.get_start_time(content)

        end_time = FormatUtils.wrap_with_format("End Time:")
        finalized_line = f"{end_time} {final_time.strftime('%H:%M')}\n"
        time_spent = FormatUtils.wrap_with_format("Time Spent:")

        breaks_seconds = self._read_breaks_seconds(content)
        hours, minutes = self.time_service.get_total_time_spent(created_time, final_time, breaks_seconds)
        total_time_line = f"{time_spent} {int(hours):02}:{int(minutes):02}\n"

        content = [
            line for line in content
            if not line.startswith(f"{end_time}") and not line.startswith(f"{time_spent}")
        ]
        content.insert(created_line_index + 1, finalized_line)
        content.insert(created_line_index + 2, total_time_line)
        self.file_service.write_lines_to_file(daily_notes_file, content)

        console.print(f"[green]✓[/green] End time: {final_time.strftime('%H:%M')}  |  Time spent: {int(hours):02}:{int(minutes):02}")

        self.cancel_alarm_for_date(final_time)

        await self._generate_and_write_summary(daily_notes_file, no_summary, force=force)

        console.print(f"[green]✓[/green] Daily notes finalized: {daily_notes_file}")

    async def _generate_and_write_summary(
        self, daily_notes_file: str, no_summary: bool, force: bool = False
    ) -> None:
        if no_summary:
            return

        note = self.parser.parse(daily_notes_file)
        if note is None:
            logger.warning("Could not parse note — skipping AI summary.")
            return

        try:
            result = await self.ai_service.summarize_day(note)
        except Exception as e:
            logger.warning(f"AI summary failed: {e}")
            return

        if not result or result.startswith("⚠️"):
            logger.warning(result if result else "AI summary was empty — no provider configured? Set AI_PROVIDER in .env.")
            return

        has_existing = any(line.strip() for line in note.summary)
        if has_existing and not force:
            self._append_ai_summary(daily_notes_file, result)
        else:
            # --force redoes the whole day: replace any prior AI summary instead of
            # stacking a new one underneath it on every re-finalize.
            self.fix_summary(daily_notes_file, result)
        console.print("[green]✓[/green] Summary generated by AI")

    def _append_ai_summary(self, file_path: str, summary_text: str) -> None:
        content = self.file_service.get_lines(file_path)
        bounds = self._summary_bounds(content)
        if bounds is None:
            return
        _, end_idx = bounds
        new_content = content[:end_idx] + [f"\n{summary_text}\n", "\n"] + content[end_idx:]
        self.file_service.write_lines_to_file(file_path, new_content)

    @staticmethod
    def _summary_bounds(content: list[str]) -> tuple[int, int] | None:
        summary_idx = next(
            (i for i, l in enumerate(content) if SECTION_SUMMARY in l and l.strip().startswith("#")),
            None,
        )
        if summary_idx is None:
            return None
        end_idx = next(
            (i for i in range(summary_idx + 1, len(content)) if content[i].strip() == "---"),
            None,
        )
        if end_idx is None:
            return None
        return summary_idx, end_idx

    def _read_breaks_seconds(self, content: list[str]) -> int:
        break_marker = FormatUtils.wrap_with_format("Break:")
        total = 0
        for line in content:
            if line.startswith(break_marker):
                time_str = line.replace(break_marker, "").strip().split()[0]
                try:
                    h, m = map(int, time_str.split(":"))
                    total += h * 3600 + m * 60
                except (ValueError, IndexError):
                    pass
        return total

    def fix_end_time_and_time_spent(self, file_path: str, end_time: datetime) -> None:
        content = self.file_service.get_lines(file_path)
        start_idx, created_time = self.time_service.get_start_time(content)

        if end_time <= created_time:
            raise ValueError(
                f"End time {end_time.strftime('%H:%M')} must be after start time {created_time.strftime('%H:%M:%S')}"
            )

        breaks_seconds = self._read_breaks_seconds(content)
        hours, minutes = self.time_service.get_total_time_spent(created_time, end_time, breaks_seconds)

        end_marker = FormatUtils.wrap_with_format("End Time:")
        spent_marker = FormatUtils.wrap_with_format("Time Spent:")

        content = [l for l in content if not l.startswith(end_marker) and not l.startswith(spent_marker)]
        content.insert(start_idx + 1, f"{end_marker} {end_time.strftime('%H:%M')}\n")
        content.insert(start_idx + 2, f"{spent_marker} {hours:02d}:{minutes:02d}\n")
        self.file_service.write_lines_to_file(file_path, content)

    def fix_time_spent_from_file(self, file_path: str) -> bool:
        content = self.file_service.get_lines(file_path)
        start_idx, created_time = self.time_service.get_start_time(content)

        end_marker = FormatUtils.wrap_with_format("End Time:")
        spent_marker = FormatUtils.wrap_with_format("Time Spent:")

        end_time_str = next(
            (l.replace(end_marker, "").strip() for l in content if l.startswith(end_marker)),
            None,
        )
        if not end_time_str:
            return False

        try:
            t = datetime.strptime(end_time_str, "%H:%M")
        except ValueError:
            return False

        end_time = created_time.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        breaks_seconds = self._read_breaks_seconds(content)
        hours, minutes = self.time_service.get_total_time_spent(created_time, end_time, breaks_seconds)

        content = [l for l in content if not l.startswith(spent_marker)]
        end_idx = next((i for i, l in enumerate(content) if l.startswith(end_marker)), start_idx)
        content.insert(end_idx + 1, f"{spent_marker} {hours:02d}:{minutes:02d}\n")
        self.file_service.write_lines_to_file(file_path, content)
        return True

    async def fix_note_automatically(self, date_str: str, file_path: str, issues: list[str]) -> list[str]:
        fixed: list[str] = []

        if "missing end time" in issues:
            lines = self.file_service.get_lines(file_path)
            _, start_time = self.time_service.get_start_time(lines)
            expected_seconds = TimeService.get_expected_workday_seconds(start_time)
            break_seconds = TimeService.get_expected_break_seconds(start_time)
            end_time = start_time + timedelta(seconds=expected_seconds + break_seconds)
            self.fix_end_time_and_time_spent(file_path, end_time)
            fixed += ["end time", "time spent"]
        elif "missing time spent" in issues and self.fix_time_spent_from_file(file_path):
            fixed.append("time spent")

        if "missing summary" in issues:
            note = self.parser.parse(file_path)
            summary = None
            if note is not None:
                try:
                    summary = await self.ai_service.summarize_day(note)
                except Exception as e:
                    logger.warning(f"AI summary failed for {date_str}: {e}")
            if summary and not summary.startswith("⚠️"):
                self.fix_summary(file_path, summary)
                fixed.append("summary")

        return fixed

    def fix_summary(self, file_path: str, summary_text: str) -> None:
        content = self.file_service.get_lines(file_path)
        bounds = self._summary_bounds(content)
        if bounds is None:
            return
        summary_idx, end_idx = bounds
        new_content = content[:summary_idx + 1] + ["\n", f"{summary_text}\n", "\n"] + content[end_idx:]
        self.file_service.write_lines_to_file(file_path, new_content)

    def daily_time(self, custom_date: datetime) -> None:
        daily_notes_file = self._get_daily_notes_file_path(custom_date)
        if exists(daily_notes_file):
            self._calculate_time(daily_notes_file)
        else:
            logger.warning(f"Daily notes file does not exist: {daily_notes_file}")

    def _calculate_time(self, daily_notes_file: str) -> None:
        started_time, elapsed_hours, finish_time = self.time_service.calculate_working_hours(daily_notes_file)
        if elapsed_hours is not None and finish_time is not None:
            console.print(f"Started time: {started_time}")
            console.print(f"Elapsed working time: {elapsed_hours:.2f}")
            console.print(f"Estimated finish time: {finish_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            logger.error("Could not calculate working hours.")

    async def sync_daily_notes(self, date: datetime) -> tuple[int, int]:
        return await self._sync.sync_daily_notes(date, self._get_daily_notes_file_path(date))

    def _insert_missing_tasks_in_section(
        self, lines: list[str], section_name: str, tasks: list[Task]
    ) -> int:
        return self._sync._insert_missing_tasks_in_section(lines, section_name, tasks)

    def _correct_stale_task_statuses(self, lines: list[str], tasks: list[Task]) -> int:
        return self._sync._correct_stale_task_statuses(lines, tasks)

    async def _correct_existing_code_review_links(self, lines: list[str]) -> int:
        return await self._sync._correct_existing_code_review_links(lines)

    def _iter_daily_notes(self, year: int):  # type: ignore[no-untyped-def]
        yield from self._audit.iter_daily_notes(year)

    def get_completion_stats(self, year: int) -> list[tuple[str, int, int]]:
        return self._statistics.get_completion_stats(year)

    def get_workload_stats(self, year: int) -> list[tuple[str, int]]:
        return self._statistics.get_workload_stats(year)

    def get_pattern_stats(self, year: int) -> dict[str, object]:
        return self._statistics.get_pattern_stats(year)

    def get_tags_stats(self, year: int) -> list[tuple[str, int]]:
        return self._statistics.get_tags_stats(year)

    def get_standup(self, today: datetime) -> dict[str, list[str]]:
        yesterday = today - timedelta(days=1)
        while yesterday.weekday() >= 5:
            yesterday -= timedelta(days=1)

        today_file = self._get_daily_notes_file_path(today)
        yesterday_file = self._get_daily_notes_file_path(yesterday)

        done: list[str] = []
        today_done: list[str] = []
        today_tasks: list[str] = []
        blockers: list[str] = []

        _done_statuses = {Status.DONE}
        _active_statuses = {Status.TODO, Status.IN_PROGRESS, Status.CODE_REVIEW}

        if exists(yesterday_file):
            note = self.parser.parse(yesterday_file)
            if note:
                done = [t.description for t in note.planned_tasks if t.status in _done_statuses]
                done += [t.description for t in note.code_review_tasks if t.status in _done_statuses]

        if exists(today_file):
            note = self.parser.parse(today_file)
            if note:
                today_done = [t.description for t in note.planned_tasks if t.status in _done_statuses]
                today_done += [t.description for t in note.code_review_tasks if t.status in _done_statuses]
                today_tasks = [t.description for t in note.planned_tasks if t.status in _active_statuses]
                today_tasks += [t.description for t in note.code_review_tasks if t.status in _active_statuses]
                blockers = [t.description for t in note.planned_tasks if t.status == Status.BLOCKED]
                blockers += [t.description for t in note.code_review_tasks if t.status == Status.BLOCKED]

        return {"done": done, "today_done": today_done, "today": today_tasks, "blockers": blockers}

    def add_note_to_daily(self, date: datetime, text: str) -> None:
        from taskjournal.services.parser import _SECTION_RULES

        file_path = self._get_daily_notes_file_path(date)
        if not exists(file_path):
            raise FileNotFoundError(f"No daily notes for {date.strftime('%Y-%m-%d')}")

        lines = self.file_service.get_lines(file_path)
        timestamp = datetime.now().strftime("%H:%M")

        in_notes = False
        last_note_idx = section_header_idx = -1

        for i, raw in enumerate(lines):
            stripped = raw.strip()
            for sec_name, pat in _SECTION_RULES:
                if pat.match(stripped):
                    in_notes = sec_name == "notes"
                    if in_notes:
                        section_header_idx = i
                    break
            if in_notes and stripped.startswith("-") and not stripped.startswith("---"):
                last_note_idx = i

        insert_at = last_note_idx if last_note_idx != -1 else section_header_idx
        if insert_at == -1:
            raise ValueError("Notes section not found in daily notes.")

        ext = ".md" if file_path.endswith(".md") else ".txt"
        prefix = " - " if ext == ".md" else ""
        lines.insert(insert_at + 1, f"{prefix}{timestamp} {text}\n")
        self.file_service.write_lines_to_file(file_path, lines)
        console.print(f"[green]✓[/green] Note added: {timestamp} {text}")
