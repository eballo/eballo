from datetime import datetime, timedelta
from os import makedirs, listdir, walk
from os.path import basename, dirname, exists, isdir, join
from pathlib import Path
from re import compile as re_compile, escape as re_escape, IGNORECASE, Pattern
from subprocess import run as subprocess_run
from sys import platform

from jinja2 import Template

from taskjournal.config import (
    TEMPLATE_FORMAT,
    DAILY_NOTES_TEMPLATE,
    BASE_DIR,
    HOLIDAYS_FILE,
    WEEK_SUMMARY_TEMPLATE,
    RETRO_TEMPLATE,
    HALF_YEAR_REVIEW_TEMPLATE,
    MONTH_REVIEW_TEMPLATE,
    ONE_ON_ONE_TEMPLATE,
)
from taskjournal.models.task import Task
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.backup import BackupService
from taskjournal.services.file import FileService
from taskjournal.services.fireman import FiremanService
from taskjournal.services.github import GithubService
from taskjournal.services.holidays import HolidayService
from taskjournal.services.jira import JiraService
from taskjournal.services.logger import logger
from taskjournal.services.ai_service import AIService
from taskjournal.services.parser import DailyParserService, _SECTION_RULES
from taskjournal.services.task_manager import TaskManager
from taskjournal.services.time import TimeService
from taskjournal.services.utils import FormatUtils
from taskjournal.services.working_days import WorkingDaysService



class CommandManager:

    def __init__(
        self,
        jira: JiraService,
        github: GithubService,
        task_formatter: TaskFormatter,
        ai_service: AIService,
        parser: DailyParserService,
        task_manager: TaskManager,
        backup_service: BackupService,
        file_service: FileService,
        time_service: TimeService,
        debug: bool = False,
    ) -> None:
        self.debug = debug
        self.jira = jira
        self.github = github
        self.task_formatter = task_formatter
        self.ai_service = ai_service
        self.parser = parser
        self.task_manager = task_manager
        self.backup_service = backup_service
        self.file_service = file_service
        self.time_service = time_service

    def _get_week_folder(self, date: datetime) -> str:
        week_folder = self.file_service.get_week_folder(BASE_DIR, date)
        makedirs(week_folder, exist_ok=True)
        return week_folder

    def _get_daily_notes_file_path(self, today: datetime) -> str:
        week_folder = self._get_week_folder(today)
        daily_notes_name = self.time_service.get_daily_notes_name(today)
        daily_notes_file = join(week_folder, daily_notes_name)
        return daily_notes_file

    def _note_issues(self, file_path: str) -> list[str]:
        """Return a list of completeness issues for a daily notes file."""
        issues: list[str] = []
        try:
            lines = self.file_service.get_lines(file_path)
            self.time_service.get_start_time(lines)
        except (ValueError, FileNotFoundError):
            issues.append("missing start time")
        if not self.file_service.check_finalized_in_file(file_path):
            issues.append("missing end time")
        data = self.parser.parse(file_path)
        if data and not str(data.get("time_spent", "")).strip():
            issues.append("missing time spent")
        if data and not any(line.strip() for line in data.get("summary", [])):
            issues.append("missing summary")
        return issues

    def audit_daily_notes(self, year: int) -> list[tuple[str, str, list[str]]]:
        """Scan all daily notes for a year. Returns (date_str, file_path, issues) tuples."""
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
                issues = self._note_issues(file_path)
                results.append((date_str, file_path, issues))

        return results

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
        """1.9 — warn before wk week report if any daily note is incomplete."""
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
            pending = []
            code_review = []
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
            logger.info("Checking for pending tasks from last week...")
            one_week_ago = create_datetime - timedelta(weeks=1)
            week_folder = self._get_week_folder(one_week_ago)
            last_week_pending_tasks = self.task_manager.get_previous_pending_tasks(
                week_folder, current_file
            )
        else:
            last_week_pending_tasks = []

        previous_pending_tasks = self.task_manager.get_previous_pending_tasks(folder_path, current_file)

        tasks = TaskManager.unique_tasks(
            default + last_week_pending_tasks + previous_pending_tasks + pending
        )

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
            code_review_tasks=self.task_formatter.format_tasks(
                code_review,
                with_name=True,
            ),
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
        logger.info(
            f"Day {day_number} of 5"
            f"  |  accumulated: {accumulated_h}h {accumulated_m:02d}m"
            f"  |  expected: {expected_h}h {expected_m:02d}m"
            f"  |  extra: {extra_sign}{extra_h}h {extra_m:02d}m"
        )
        streak = self.get_streak_stats(create_datetime)
        logger.info(f"Streak: {streak['current']} day(s)  |  all-time best: {streak['longest']} day(s)")
        logger.info(
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
            result = subprocess_run(
                ["at", finish_str], input=script.encode(), capture_output=True
            )
            if result.returncode == 0:
                logger.info(f"Alarm set for {finish_str} — end of scheduled workday")
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
                logger.info(f"Alarm cancelled (job {job_id})")
            else:
                logger.debug(f"Could not cancel alarm job {job_id}: {result.stderr.decode().strip()}")
        except Exception as e:
            logger.debug(f"Could not cancel alarm: {e}")

    def list_tasks_in_daily(self, date: datetime) -> list[Task]:
        file_path = self._get_daily_notes_file_path(date)
        if not exists(file_path):
            return []
        data = self.parser.parse(file_path)
        return data.get("planned_tasks", []) if data else []

    def add_task_to_daily(self, date: datetime, description: str) -> None:
        file_path = self._get_daily_notes_file_path(date)
        if not exists(file_path):
            raise FileNotFoundError(f"No daily notes for {date.strftime('%Y-%m-%d')}")

        ext = ".md" if file_path.endswith(".md") else ".txt"
        lines = self.file_service.get_lines(file_path)
        task_rx: Pattern[str] = re_compile(r"^\s*-?\s*\[[ xX>~-]\]")

        in_planned = False
        last_task_idx = -1
        section_header_idx = -1

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
            raise ValueError("Planned Tasks section not found in daily notes.")

        prefix = " - " if ext == ".md" else ""
        lines.insert(insert_at + 1, f"{prefix}[ ] {description}\n")
        self.file_service.write_lines_to_file(file_path, lines)
        logger.info(f"Task added: {description}")

    def _update_task_status(self, date: datetime, description: str, new_char: str) -> bool:
        file_path = self._get_daily_notes_file_path(date)
        if not exists(file_path):
            raise FileNotFoundError(f"No daily notes for {date.strftime('%Y-%m-%d')}")

        lines = self.file_service.get_lines(file_path)
        needle = description.strip().lower()
        task_rx: Pattern[str] = re_compile(r"\[([ xX>~-])\](\s*)(.*)")

        for i, raw in enumerate(lines):
            m = task_rx.search(raw)
            if m:
                task_text = m.group(3).strip().lower()
                if needle in task_text or task_text in needle:
                    lines[i] = raw.replace(f"[{m.group(1)}]", f"[{new_char}]", 1)
                    self.file_service.write_lines_to_file(file_path, lines)
                    return True

        return False

    def complete_task_in_daily(self, date: datetime, description: str) -> bool:
        return self._update_task_status(date, description, "x")

    def block_task_in_daily(self, date: datetime, description: str) -> bool:
        return self._update_task_status(date, description, "-")

    def wip_task_in_daily(self, date: datetime, description: str) -> bool:
        return self._update_task_status(date, description, ">")

    def search_notes(
        self,
        query: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        note_type: str | None = None,
    ) -> list[tuple[str, int, str]]:
        results: list[tuple[str, int, str]] = []
        pattern: Pattern[str] = re_compile(re_escape(query), IGNORECASE)
        date_rx: Pattern[str] = re_compile(r"^(\d{4}-\d{2}-\d{2})")

        for root, dirs, files in walk(str(BASE_DIR)):
            dirs.sort()
            for fname in sorted(files):
                if not fname.endswith(f".{TEMPLATE_FORMAT}"):
                    continue
                if note_type == "daily" and "DailyNotes" not in fname:
                    continue
                if note_type == "week" and "week-summary" not in fname:
                    continue

                if from_date or to_date:
                    dm = date_rx.match(fname)
                    if dm:
                        try:
                            fdate = datetime.strptime(dm.group(1), "%Y-%m-%d")
                            if from_date and fdate < from_date:
                                continue
                            if to_date and fdate > to_date:
                                continue
                        except ValueError:
                            pass

                file_path = join(root, fname)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        for lineno, line in enumerate(f, 1):
                            if pattern.search(line):
                                results.append((file_path, lineno, line.rstrip()))
                except OSError:
                    pass

        return results

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
            line
            for line in content
            if not line.startswith(f"{end_time}")
            and not line.startswith(f"{time_spent}")
        ]

        content.insert(created_line_index + 1, finalized_line)
        content.insert(created_line_index + 2, total_time_line)
        self.file_service.write_lines_to_file(daily_notes_file, content)

        logger.info(f"Daily notes finalized {daily_notes_file}")

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

    async def create_week_summary(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        summary_file = join(week_folder, f"week-summary.{TEMPLATE_FORMAT}")
        week_summary_content = self.file_service.load_template(WEEK_SUMMARY_TEMPLATE)

        self._warn_incomplete_week_notes(custom_date, week_folder)

        working_days_service = WorkingDaysService(year=custom_date.year, parser=self.parser)
        stats = working_days_service.get_week_stats(custom_date, week_folder)

        is_fireman_week = FiremanService(custom_date).is_fireman_week()

        total_hours, total_minutes = self.time_service.seconds_to_hours_minutes(stats["total_time_seconds"])

        summary = []
        for file_name in sorted(listdir(week_folder)):
            if file_name.endswith(f"-DailyNotes.{TEMPLATE_FORMAT}"):
                daily_file_path = join(week_folder, file_name)
                summary.append(self.file_service.get_summary_from_daily_notes(daily_file_path))

        summary_ai = await self.ai_service.summarize(
            summary, stats=stats, is_fireman_week=is_fireman_week
        )

        week_summary_content = Template(week_summary_content).render(
            start_date=stats["start_date"].strftime("%Y-%m-%d"),
            end_date=stats["end_date"].strftime("%Y-%m-%d"),
            total_time=f" {total_hours} hours and {total_minutes} minutes",
            total_worked_days=str(stats["total_worked_days"]),
            vacation_days=str(stats["vacation_days"]),
            days_at_office=str(stats["days_at_office"]),
            days_at_home=str(stats["days_at_home"]),
            is_fireman_week="Yes" if is_fireman_week else "No",
            summary=summary_ai,
        )

        self.file_service.write_to_file(summary_file, week_summary_content)

        logger.info(f"Week summary file created at: {summary_file}")

        return None

    async def recreate_week_summaries(
        self, start_date: datetime, end_date: datetime
    ) -> None:
        current_date = start_date - timedelta(days=start_date.weekday())

        while current_date <= end_date:
            logger.info(
                f"Recreating week summary for week starting {current_date.strftime('%Y-%m-%d')}..."
            )
            await self.create_week_summary(current_date)
            current_date += timedelta(days=7)

        return None

    async def create_half_year_review(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)

        half_year_review_file = join(
            week_folder, f"half-year.{TEMPLATE_FORMAT}"
        )
        half_year_content = self.file_service.load_template(HALF_YEAR_REVIEW_TEMPLATE)

        tasks = await self.jira.get_current_tasks_assigned_to_me_last_6_months()
        epics = TaskManager.get_unique_epics(tasks)
        total_tasks = len(tasks)
        total_epics = len(epics)

        async with self.github:
            github_contributions = await self.github.get_contributions_last_6_months()

        half_year_content = Template(half_year_content).render(
            total_tasks=str(total_tasks),
            total_epics=str(total_epics),
            github_contributions=str(github_contributions),
            tasks="\n".join(f"{task}" for task in tasks),
            epics="\n".join(f"{epic}" for epic in epics),
        )

        self.file_service.write_to_file(half_year_review_file, half_year_content)

        logger.info(f"Half year review file created: {half_year_review_file}")

        return None

    async def create_month_review(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        month_review_file = join(week_folder, f"month.{TEMPLATE_FORMAT}")
        month_content = self.file_service.load_template(MONTH_REVIEW_TEMPLATE)

        working_days_service = WorkingDaysService(year=custom_date.year, parser=self.parser, debug=self.debug)
        stats = working_days_service.get_month_stats(custom_date, str(BASE_DIR))

        tasks = await self.jira.get_current_tasks_assigned_to_me_last_month()
        epics = TaskManager.get_unique_epics(tasks)
        total_tasks = len(tasks)
        total_epics = len(epics)

        async with self.github:
            github_contributions = await self.github.get_contributions_last_month()

        summary = await self.ai_service.summarize(
            stats["daily_summaries"],
            stats=stats,
            is_fireman_week=False,
            period="monthly",
        )

        total_hours, total_minutes = self.time_service.seconds_to_hours_minutes(stats["total_time_seconds"])
        total_time_str = f"{total_hours}h {total_minutes}m"

        month_content = Template(month_content).render(
            start_date=stats["start_date"].strftime("%Y-%m-%d"),
            end_date=stats["end_date"].strftime("%Y-%m-%d"),
            total_time=total_time_str,
            total_worked_days=str(stats["total_worked_days"]),
            vacation_days=str(stats["vacation_days"]),
            days_at_office=str(stats["days_at_office"]),
            days_at_home=str(stats["days_at_home"]),
            total_tasks=str(total_tasks),
            total_epics=str(total_epics),
            github_contributions=str(github_contributions),
            epics="\n".join(f"{epic}" for epic in epics),
            summary=summary,
        )

        self.file_service.write_to_file(month_review_file, month_content)
        logger.info(f"Month review file created: {month_review_file}")

        return None

    def create_retro(self, custom_date: datetime) -> None:
        week_folder = self._get_week_folder(custom_date)
        retro_file = join(week_folder, f"retro.{TEMPLATE_FORMAT}")

        if not exists(retro_file):
            template_content = self.file_service.load_template(RETRO_TEMPLATE)

            sprint = self.jira.get_active_sprint()
            sprint_name = sprint.name if sprint else "No active sprint"
            template_content = Template(template_content).render(sprint_name=sprint_name)

            self.file_service.write_to_file(retro_file, template_content)
            logger.info(f"Retro file ensured: {retro_file}")

        return None

    def create_one_on_one(self, custom_date: datetime) -> None:
        one_one_one_file_name = self.time_service.get_1on1_name(custom_date)
        one_one_one_file = join(
            BASE_DIR, f"{custom_date.year}/1on1s/{one_one_one_file_name}"
        )

        if not exists(one_one_one_file):
            makedirs(str(Path(one_one_one_file).parent), exist_ok=True)
            template_content = self.file_service.load_template(ONE_ON_ONE_TEMPLATE)
            self.file_service.write_to_file(one_one_one_file, template_content)
            logger.info(f"1on1 file ensured: {one_one_one_file}")

        return None

    def add_topic_to_one_on_one(self, date: datetime, topic: str) -> None:
        self.create_one_on_one(date)
        file_path = join(str(BASE_DIR), f"{date.year}/1on1s/{self.time_service.get_1on1_name(date)}")

        lines = self.file_service.get_lines(file_path)
        bullet_rx: Pattern[str] = re_compile(r"^-\s+")

        in_proposal = False
        last_bullet_idx = -1
        section_header_idx = -1

        for i, raw in enumerate(lines):
            stripped = raw.strip()
            if stripped.startswith("#"):
                in_proposal = "Proposal" in stripped or "topic" in stripped.lower()
                if in_proposal:
                    section_header_idx = i
                elif in_proposal:
                    in_proposal = False
            elif in_proposal and bullet_rx.match(stripped):
                last_bullet_idx = i

        insert_at = last_bullet_idx if last_bullet_idx != -1 else section_header_idx
        if insert_at == -1:
            raise ValueError("'Proposal topics' section not found in 1on1 file.")

        lines.insert(insert_at + 1, f"- {topic}\n")
        self.file_service.write_lines_to_file(file_path, lines)
        logger.info(f"Topic added: {topic}")

    def get_streak_stats(self, today: datetime) -> dict[str, object]:
        from datetime import date as date_t, timedelta as td
        date_rx: Pattern[str] = re_compile(r"^(\d{4}-\d{2}-\d{2})")

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

        # Current streak: walk backwards skipping non-working days
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

        # All-time longest streak
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

    async def sync_daily_notes(self, date: datetime) -> None:
        file_path = self._get_daily_notes_file_path(date)
        if not exists(file_path):
            raise FileNotFoundError(f"No daily notes for {date.strftime('%Y-%m-%d')}")

        logger.info("Fetching Jira tasks...")
        pending = await self.jira.get_current_sprint_tasks_not_done_assigned_to_me()
        code_review = await self.jira.get_current_sprint_tasks_in_code_review()
        await self.github.update_status_if_task_reviewed(code_review)

        existing_data = self.parser.parse(file_path)
        existing_tasks = existing_data.get("planned_tasks", []) if existing_data else []
        existing_descs = [t.description.lower() for t in existing_tasks]

        to_add = [
            t for t in pending
            if not any(
                (t.key and t.key in desc) or t.description.strip().lower() in desc
                for desc in existing_descs
            )
        ]

        if not to_add:
            logger.info("All Jira tasks already present in daily notes.")
            return

        lines = self.file_service.get_lines(file_path)
        task_rx: Pattern[str] = re_compile(r"^\s*-?\s*\[[ xX>~-]\]")
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
            logger.info(f"Added: {task.description}")

        self.file_service.write_lines_to_file(file_path, lines)

    def create_backup(self) -> None:
        backup_file = self.backup_service.create()
        logger.info(f"Backup created at: {backup_file}")

    def show_info(self, today: datetime) -> None:
        day_name = today.strftime("%A")
        week_number = today.isocalendar()[1]

        logger.info(f"📅 Today is {day_name}, {today.strftime('%Y-%m-%d')}")
        logger.info(f"🔢 We are in week {week_number}")

    def _calculate_time(self, daily_notes_file: str) -> None:
        started_time, elapsed_hours, finish_time = self.time_service.calculate_working_hours(
            daily_notes_file
        )
        if elapsed_hours is not None and finish_time is not None:
            logger.info(f"Started time: {started_time}")
            logger.info(f"Elapsed working time: {elapsed_hours:.2f}")
            logger.info(
                f"Estimated finish time: {finish_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            logger.error("Could not calculate working hours.")
