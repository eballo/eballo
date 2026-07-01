from datetime import datetime, timedelta, date as date_t
from os import makedirs, listdir, walk
from os.path import basename, dirname, exists, isdir, join
from pathlib import Path
from subprocess import run as subprocess_run
from sys import platform

from jinja2 import Template

from taskjournal.config import (
    TEMPLATE_FORMAT,
    DAILY_NOTES_TEMPLATE,
    BASE_DIR,
    HOLIDAYS_FILE,
)
from taskjournal.models.task import Task
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.file import FileService
from taskjournal.services.fireman import FiremanService
from taskjournal.services.github import GithubService
from taskjournal.services.holidays import HolidayService
from taskjournal.services.jira import JiraService
from taskjournal.services.logger import console, logger
from taskjournal.services.parser import DailyParserService
from taskjournal.services.task_manager import TaskManager
from taskjournal.services.time import TimeService
from taskjournal.services.utils import FormatUtils


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
        debug: bool = False,
    ) -> None:
        self.debug = debug
        self.jira = jira
        self.github = github
        self.task_formatter = task_formatter
        self.parser = parser
        self.task_manager = task_manager
        self.file_service = file_service
        self.time_service = time_service

    def _get_week_folder(self, date: datetime) -> str:
        week_folder = self.file_service.get_week_folder(BASE_DIR, date)
        makedirs(week_folder, exist_ok=True)
        return week_folder

    def _get_daily_notes_file_path(self, today: datetime) -> str:
        week_folder = self._get_week_folder(today)
        daily_notes_name = self.time_service.get_daily_notes_name(today)
        return join(week_folder, daily_notes_name)

    def _note_issues(self, file_path: str) -> list[str]:
        issues: list[str] = []
        try:
            lines = self.file_service.get_lines(file_path)
            self.time_service.get_start_time(lines)
        except (ValueError, FileNotFoundError):
            issues.append("missing start time")
        if not self.file_service.check_finalized_in_file(file_path):
            issues.append("missing end time")
        note = self.parser.parse(file_path)
        if note and not note.time_spent.strip():
            issues.append("missing time spent")
        if note and not any(line.strip() for line in note.summary):
            issues.append("missing summary")
        return issues

    def audit_daily_notes(self, year: int) -> list[tuple[str, str, list[str]]]:
        year_dir = join(str(BASE_DIR), str(year))
        if not exists(year_dir):
            return []

        results: list[tuple[str, str, list[str]]] = []
        for entry in sorted(listdir(year_dir)):
            week_path = join(year_dir, entry)
            if not isdir(week_path):
                continue
            for file_name in sorted(listdir(week_path)):
                if not file_name.endswith(f"-DailyNotes.{TEMPLATE_FORMAT}"):
                    continue
                file_path = join(week_path, file_name)
                date_str = file_name.replace(f"-DailyNotes.{TEMPLATE_FORMAT}", "")
                results.append((date_str, file_path, self._note_issues(file_path)))

        return results

    def count_week_folders(self, year: int) -> int:
        year_dir = join(str(BASE_DIR), str(year))
        if not exists(year_dir):
            return 0
        return sum(1 for e in listdir(year_dir) if e.startswith("week") and isdir(join(year_dir, e)))

    def audit_weekly_coverage(self, year: int) -> list[tuple[str, list[str]]]:
        year_dir = join(str(BASE_DIR), str(year))
        if not exists(year_dir):
            return []

        today = date_t.today()
        missing: list[tuple[str, list[str]]] = []

        for entry in sorted(listdir(year_dir)):
            if not entry.startswith("week"):
                continue
            week_path = join(year_dir, entry)
            if not isdir(week_path):
                continue
            try:
                week_num = int(entry[4:])
            except ValueError:
                continue

            week_missing: list[str] = []
            for day_num in range(1, 6):
                try:
                    day = date_t.fromisocalendar(year, week_num, day_num)
                except ValueError:
                    continue
                if day > today:
                    continue
                daily_path = join(week_path, f"{day}-DailyNotes.{TEMPLATE_FORMAT}")
                holiday_path = join(week_path, f"{day}-DailyNotes-Holidays.{TEMPLATE_FORMAT}")
                if not exists(daily_path) and not exists(holiday_path):
                    week_missing.append(str(day))

            if week_missing:
                missing.append((entry, week_missing))

        return missing

    def get_previous_day_issues(self, today: datetime) -> tuple[str, str, list[str]] | None:
        candidate = today - timedelta(days=1)
        for _ in range(14):
            prev_file = self._get_daily_notes_file_path(candidate)
            if exists(prev_file):
                issues = self._note_issues(prev_file)
                return (candidate.strftime("%Y-%m-%d"), prev_file, issues) if issues else None
            candidate -= timedelta(days=1)
        return None

    def _warn_incomplete_week_notes(self, week_date: datetime, week_folder: str) -> None:
        start_of_week = week_date - timedelta(days=week_date.weekday())
        incomplete: list[str] = []

        for i in range(5):
            day = start_of_week + timedelta(days=i)
            daily_file = join(week_folder, self.time_service.get_daily_notes_name(day))
            if not exists(daily_file):
                continue
            issues = self._note_issues(daily_file)
            if issues:
                incomplete.append(f"{day.strftime('%Y-%m-%d')}: {', '.join(issues)}")

        if incomplete:
            logger.warning("Week report generated with incomplete notes:")
            for line in incomplete:
                logger.warning(f"  ⚠  {line}")

    def get_streak_stats(self, today: datetime) -> dict[str, object]:
        from re import compile as re_compile
        from datetime import timedelta as td

        date_rx = re_compile(r"^(\d{4}-\d{2}-\d{2})")
        all_dates: set[date_t] = set()
        for root, _, files in walk(str(BASE_DIR)):
            for fname in files:
                if "DailyNotes" not in fname:
                    continue
                dm = date_rx.match(fname)
                if dm:
                    try:
                        all_dates.add(datetime.strptime(dm.group(1), "%Y-%m-%d").date())
                    except ValueError:
                        pass

        if not all_dates:
            return {"current": 0, "longest": 0, "longest_start": None, "longest_end": None, "total": 0}

        holiday_cache: dict[int, HolidayService] = {}

        def _is_non_working(d: date_t) -> bool:
            if d.weekday() >= 5:
                return True
            if d.year not in holiday_cache:
                path = join(str(BASE_DIR), f"{d.year}/{HOLIDAYS_FILE}")
                holiday_cache[d.year] = HolidayService(filepath=path)
            return holiday_cache[d.year].is_holiday(datetime(d.year, d.month, d.day)) is not None

        def _next_working(d: date_t) -> date_t:
            d += td(days=1)
            while _is_non_working(d):
                d += td(days=1)
            return d

        today_date = today.date()
        current = 0
        check = today_date
        while True:
            if _is_non_working(check):
                check -= td(days=1)
                continue
            if check not in all_dates:
                break
            current += 1
            check -= td(days=1)

        sorted_dates = sorted(all_dates)
        longest = cur_len = 1
        longest_start = longest_end = cur_start = sorted_dates[0]

        for i in range(1, len(sorted_dates)):
            prev, curr = sorted_dates[i - 1], sorted_dates[i]
            if curr == _next_working(prev):
                cur_len += 1
            else:
                cur_len = 1
                cur_start = curr

            if cur_len > longest:
                longest = cur_len
                longest_start = cur_start
                longest_end = curr

        return {
            "current": current,
            "longest": longest,
            "longest_start": longest_start,
            "longest_end": longest_end,
            "total": len(all_dates),
        }

    async def create_daily_notes(
        self,
        create_datetime: datetime,
        force: bool = False,
        firefighter: bool = False,
        work_from: str | None = None,
        offline: bool = False,
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
        tasks = TaskManager.unique_tasks(default + last_week_pending_tasks + previous_pending_tasks + pending)

        daily_notes_content = Template(template_content).render(
            day_name=create_datetime.strftime("%A"),
            date=create_datetime.strftime("%Y-%m-%d"),
            start_time=create_datetime.strftime("%H:%M:%S"),
            end_time="",
            break_time="01:00",
            time_spent="",
            work_from=work_from,
            sprint_name=sprint_name,
            tasks=self.task_formatter.format_tasks(tasks, with_name=True),
            code_review_tasks=self.task_formatter.format_tasks(code_review, with_name=True),
            notes="-",
            summary="",
            firefighter=firefighter,
            firefighter_notes="-",
            extra="",
        )

        self.file_service.write_to_file(daily_notes_file, daily_notes_content)

        week_folder = self._get_week_folder(create_datetime)
        accumulated_seconds = self.time_service.get_accumulated_week_seconds(week_folder, create_datetime)
        weekday = create_datetime.weekday()
        days_before_today = min(weekday, 5)
        expected_seconds = days_before_today * 8 * 3600
        extra_seconds = accumulated_seconds - expected_seconds
        today_work_seconds = max(0, 8 * 3600 - extra_seconds)
        finish = self.time_service.estimated_finish_time(create_datetime, accumulated_seconds, days_before_today)

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
        console.print(
            f"Today: {today_h}h {today_m:02d}m work + 1h lunch"
            f"  →  estimated finish {finish.strftime('%H:%M')}"
        )
        alarm_file = join(week_folder, f".alarm_job_{create_datetime.strftime('%Y-%m-%d')}")
        self._schedule_macos_alarm(finish, alarm_file)
        return None

    def _schedule_macos_alarm(self, finish_time: datetime, alarm_file: str) -> None:
        if platform != "darwin":
            return
        finish_str = finish_time.strftime("%H:%M")
        script = 'osascript -e \'display notification "Time to wrap up!" with title "wk journal"\''
        try:
            from re import compile as re_compile
            result = subprocess_run(["at", finish_str], input=script.encode(), capture_output=True)
            if result.returncode == 0:
                console.print(f"[dim]Alarm set for {finish_str} — end of scheduled workday[/dim]")
                m = re_compile(r"job\s+(\d+)").search(result.stderr.decode())
                if m:
                    Path(alarm_file).write_text(m.group(1))
            else:
                logger.debug(f"Could not schedule alarm: {result.stderr.decode().strip()}")
        except Exception as e:
            logger.debug(f"Could not schedule alarm: {e}")

    def _cancel_macos_alarm(self, alarm_file: str) -> None:
        if platform != "darwin":
            return
        alarm_path = Path(alarm_file)
        if not alarm_path.exists():
            return
        try:
            job_id = alarm_path.read_text().strip()
            result = subprocess_run(["atrm", job_id], capture_output=True)
            alarm_path.unlink()
            if result.returncode == 0:
                console.print(f"[dim]Alarm cancelled (job {job_id})[/dim]")
            else:
                logger.debug(f"Could not cancel alarm job {job_id}: {result.stderr.decode().strip()}")
        except Exception as e:
            logger.debug(f"Could not cancel alarm: {e}")

    def finalize_daily_notes(self, custom_date: datetime) -> None:
        daily_notes_file = self._get_daily_notes_file_path(custom_date)

        if not exists(daily_notes_file):
            logger.error(f"Daily notes file does not exist: {daily_notes_file}")
            return None

        if self.file_service.check_finalized_in_file(daily_notes_file):
            logger.warning(f"File '{daily_notes_file}' is already finalized.")
            return None

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

        console.print(f"[green]✓[/green] Daily notes finalized: {daily_notes_file}")

        alarm_file = join(dirname(daily_notes_file), f".alarm_job_{final_time.strftime('%Y-%m-%d')}")
        self._cancel_macos_alarm(alarm_file)

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

    def fix_summary(self, file_path: str, summary_text: str) -> None:
        content = self.file_service.get_lines(file_path)

        summary_idx = next(
            (i for i, l in enumerate(content) if "Summary" in l and l.strip().startswith("#")),
            None,
        )
        if summary_idx is None:
            return

        end_idx = next(
            (i for i in range(summary_idx + 1, len(content)) if content[i].strip() == "---"),
            None,
        )
        if end_idx is None:
            return

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

    async def sync_daily_notes(self, date: datetime) -> None:
        from re import compile as re_compile
        from taskjournal.services.parser import _SECTION_RULES

        file_path = self._get_daily_notes_file_path(date)
        if not exists(file_path):
            raise FileNotFoundError(f"No daily notes for {date.strftime('%Y-%m-%d')}")

        logger.debug("Fetching Jira tasks...")
        pending = await self.jira.get_current_sprint_tasks_not_done_assigned_to_me()
        code_review = await self.jira.get_current_sprint_tasks_in_code_review()
        await self.github.update_status_if_task_reviewed(code_review)

        existing_data = self.parser.parse(file_path)
        existing_tasks = existing_data.planned_tasks if existing_data else []
        existing_descs = [t.description.lower() for t in existing_tasks]

        to_add = [
            t for t in pending
            if not any(
                (t.key and t.key in desc) or t.description.strip().lower() in desc
                for desc in existing_descs
            )
        ]

        if not to_add:
            console.print("[green]✓[/green] All Jira tasks already present in daily notes.")
            return

        lines = self.file_service.get_lines(file_path)
        task_rx = re_compile(r"^\s*-?\s*\[[ xX>~-]\]")
        in_planned = False
        last_task_idx = section_header_idx = -1

        for i, raw in enumerate(lines):
            stripped = raw.strip()
            for sec_name, pat in _SECTION_RULES:
                if pat.match(stripped):
                    in_planned = sec_name == "planned_tasks"
                    if in_planned:
                        section_header_idx = i
                    break
            if in_planned and task_rx.match(stripped):
                last_task_idx = i

        insert_at = last_task_idx if last_task_idx != -1 else section_header_idx
        if insert_at == -1:
            raise ValueError("Planned Tasks section not found.")

        for offset, task in enumerate(to_add):
            formatted = self.task_formatter.format_task(task, with_name=True, with_status=False)
            lines.insert(insert_at + 1 + offset, formatted + "\n")
            console.print(f"  [green]+[/green] {task.description}")

        self.file_service.write_lines_to_file(file_path, lines)
