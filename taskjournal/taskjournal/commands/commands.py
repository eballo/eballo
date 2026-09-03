from datetime import datetime

from taskjournal.commands.admin import AdminCommands
from taskjournal.commands.daily import DailyCommands
from taskjournal.commands.pr import PRCommands
from taskjournal.commands.reports import ReportCommands
from taskjournal.commands.search import SearchCommands
from taskjournal.commands.tasks import TaskCommands
from taskjournal.models.github import PullRequest, RepoCommitStat
from taskjournal.models.task import Task
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.ai.base import AIService
from taskjournal.services.backup import BackupService
from taskjournal.services.feedback import FeedbackService
from taskjournal.services.file import FileService
from taskjournal.services.integrations.github import GithubService
from taskjournal.services.integrations.jira import JiraService
from taskjournal.services.integrations.screentime import ScreenTimeService
from taskjournal.services.parser import DailyParserService
from taskjournal.services.recurring import RecurringTasksService
from taskjournal.services.schedule import ScheduleService
from taskjournal.services.task_manager import TaskManager
from taskjournal.services.time import TimeService


class CommandManager:
    """Thin facade — delegates every call to the appropriate domain class."""

    def __init__(
        self,
        jira: JiraService,
        github: GithubService,
        task_formatter: TaskFormatter,
        ai_service: AIService,
        parser: DailyParserService,
        task_manager: TaskManager,
        backup_service: BackupService,
        schedule_service: ScheduleService,
        file_service: FileService,
        time_service: TimeService,
        recurring_service: RecurringTasksService | None = None,
        feedback_service: FeedbackService | None = None,
        screen_time_service: ScreenTimeService | None = None,
        daily_alarms_enabled: bool = True,
        debug: bool = False,
    ) -> None:
        self.jira = jira
        self.github = github
        self.parser = parser
        self.ai_service = ai_service
        self.file_service = file_service
        self.time_service = time_service
        self.task_manager = task_manager
        self.task_formatter = task_formatter
        self.backup_service = backup_service
        self.schedule_service = schedule_service

        self._recurring = recurring_service or RecurringTasksService()
        self._feedback = feedback_service
        self._screen_time = screen_time_service
        self._daily = DailyCommands(
            jira=jira,
            github=github,
            task_formatter=task_formatter,
            parser=parser,
            task_manager=task_manager,
            file_service=file_service,
            time_service=time_service,
            ai_service=ai_service,
            recurring_service=self._recurring,
            daily_alarms_enabled=daily_alarms_enabled,
            debug=debug,
        )
        self._tasks = TaskCommands(
            parser=parser,
            file_service=file_service,
            time_service=time_service,
            task_formatter=task_formatter,
        )
        self._reports = ReportCommands(
            jira=jira,
            github=github,
            ai_service=ai_service,
            parser=parser,
            file_service=file_service,
            time_service=time_service,
            debug=debug,
        )
        self._search = SearchCommands()
        self._pr = PRCommands(
            github=github,
            task_commands=self._tasks,
            task_manager=task_manager,
        )
        self._admin = AdminCommands(
            backup_service=backup_service,
            schedule_service=schedule_service,
            time_service=time_service,
            jira=jira,
            github=github,
            ai_service=ai_service,
        )

    # ── Daily ─────────────────────────────────────────────────────────────────

    async def create_daily_notes(
        self,
        create_datetime: datetime,
        force: bool = False,
        firefighter: bool = False,
        work_from: str | None = None,
        offline: bool = False,
        energy: int | None = None,
    ) -> None:
        return await self._daily.create_daily_notes(
            create_datetime, force=force, firefighter=firefighter,
            work_from=work_from, offline=offline, energy=energy,
        )

    async def finalize_daily_notes(self, custom_date: datetime, no_summary: bool = False, force: bool = False) -> None:
        return await self._daily.finalize_daily_notes(custom_date, no_summary=no_summary, force=force)

    def get_standup(self, today: datetime) -> dict[str, list[str]]:
        return self._daily.get_standup(today)

    def add_recurring_task(self, description: str, days: list[str] | None = None, monthly: bool = False) -> None:
        self._recurring.add(description, days, monthly)

    def remove_recurring_task(self, description: str) -> bool:
        return self._recurring.remove(description)

    def list_recurring_tasks(self) -> list[dict[str, object]]:
        return self._recurring.list_all()

    def get_completion_stats(self, year: int) -> list[tuple[str, int, int]]:
        return self._daily.get_completion_stats(year)

    def get_workload_stats(self, year: int) -> list[tuple[str, int]]:
        return self._daily.get_workload_stats(year)

    def get_pattern_stats(self, year: int) -> dict[str, object]:
        return self._daily.get_pattern_stats(year)

    def get_tags_stats(self, year: int) -> list[tuple[str, int]]:
        return self._daily.get_tags_stats(year)

    def add_note_to_daily(self, date: datetime, text: str) -> None:
        return self._daily.add_note_to_daily(date, text)

    def daily_time(self, custom_date: datetime) -> None:
        return self._daily.daily_time(custom_date)

    def fix_end_time_and_time_spent(self, file_path: str, end_time: datetime) -> None:
        return self._daily.fix_end_time_and_time_spent(file_path, end_time)

    def fix_time_spent_from_file(self, file_path: str) -> bool:
        return self._daily.fix_time_spent_from_file(file_path)

    def fix_summary(self, file_path: str, summary_text: str) -> None:
        return self._daily.fix_summary(file_path, summary_text)

    async def fix_note_automatically(self, date_str: str, file_path: str, issues: list[str]) -> list[str]:
        return await self._daily.fix_note_automatically(date_str, file_path, issues)

    def audit_daily_notes(self, year: int) -> list[tuple[str, str, list[str]]]:
        return self._daily.audit_daily_notes(year)

    def count_week_folders(self, year: int) -> int:
        return self._daily.count_week_folders(year)

    def audit_weekly_coverage(self, year: int) -> list[tuple[str, list[str]]]:
        return self._daily.audit_weekly_coverage(year)

    def get_previous_day_issues(self, today: datetime) -> tuple[str, str, list[str]] | None:
        return self._daily.get_previous_day_issues(today)

    def get_streak_stats(self, today: datetime) -> dict[str, object]:
        return self._daily.get_streak_stats(today)

    async def sync_daily_notes(self, date: datetime) -> tuple[int, int]:
        return await self._daily.sync_daily_notes(date)

    def _get_week_folder(self, date: datetime) -> str:
        return self._daily._get_week_folder(date)

    def _get_daily_notes_file_path(self, today: datetime) -> str:
        return self._daily._get_daily_notes_file_path(today)

    def _note_issues(self, file_path: str) -> list[str]:
        return self._daily._note_issues(file_path)

    def _schedule_macos_alarm(self, finish_time: datetime, alarm_file: str) -> None:
        return self._daily._schedule_macos_alarm(finish_time, alarm_file)

    def _cancel_macos_alarm(self, alarm_file: str) -> None:
        return self._daily._cancel_macos_alarm(alarm_file)

    def list_alarms(self, weeks_back: int = 4) -> list[dict[str, object]]:
        return self._daily.list_alarms(weeks_back)

    def set_alarm(
        self, date: datetime, alarm_time: datetime, message: str = "Time to wrap up!"
    ) -> None:
        return self._daily.set_alarm(date, alarm_time, message)

    def cancel_alarm_for_date(self, date: datetime) -> bool:
        return self._daily.cancel_alarm_for_date(date)

    def _calculate_time(self, daily_notes_file: str) -> None:
        return self._daily._calculate_time(daily_notes_file)

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def list_tasks_in_daily(self, date: datetime) -> list[Task]:
        return self._tasks.list_tasks_in_daily(date)

    def add_task_to_daily(self, date: datetime, description: str) -> None:
        return self._tasks.add_task_to_daily(date, description)

    def complete_task_in_daily(self, date: datetime, description: str) -> bool:
        return self._tasks.complete_task_in_daily(date, description)

    def block_task_in_daily(self, date: datetime, description: str) -> bool:
        return self._tasks.block_task_in_daily(date, description)

    def wip_task_in_daily(self, date: datetime, description: str) -> bool:
        return self._tasks.wip_task_in_daily(date, description)

    # ── Reports ───────────────────────────────────────────────────────────────

    async def create_week_summary(self, custom_date: datetime, tickets: bool = False) -> None:
        return await self._reports.create_week_summary(custom_date, tickets=tickets)

    async def recreate_week_summaries(self, start_date: datetime, end_date: datetime) -> None:
        return await self._reports.recreate_week_summaries(start_date, end_date)

    async def create_half_year_review(self, custom_date: datetime) -> None:
        return await self._reports.create_half_year_review(custom_date)

    async def create_month_review(self, custom_date: datetime) -> None:
        return await self._reports.create_month_review(custom_date)

    async def create_quarter_review(self, custom_date: datetime) -> None:
        return await self._reports.create_quarter_review(custom_date)

    async def create_year_review(self, custom_date: datetime) -> None:
        return await self._reports.create_year_review(custom_date)

    def compare_periods(self, period: str, year: int) -> list[dict[str, object]]:
        return self._reports.compare_periods(period, year)

    def create_retro(self, custom_date: datetime) -> None:
        return self._reports.create_retro(custom_date)

    def create_one_on_one(self, custom_date: datetime, person_name: str = "") -> None:
        return self._reports.create_one_on_one(custom_date, person_name=person_name)

    def add_topic_to_one_on_one(self, date: datetime, topic: str) -> None:
        return self._reports.add_topic_to_one_on_one(date, topic)

    # ── Search ────────────────────────────────────────────────────────────────

    def search_notes(
        self,
        query: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        note_type: str | None = None,
    ) -> list[tuple[str, int, str]]:
        return self._search.search_notes(query, from_date=from_date, to_date=to_date, note_type=note_type)

    # ── Admin ─────────────────────────────────────────────────────────────────

    def create_backup(self) -> None:
        return self._admin.create_backup()

    def schedule_backup(self, hour: int, minute: int) -> None:
        return self._admin.schedule_backup(hour, minute)

    def disable_backup_schedule(self) -> None:
        return self._admin.disable_backup_schedule()

    def show_info(self, today: datetime) -> None:
        return self._admin.show_info(today)

    async def get_jira_tasks(self, mode: str = "") -> list[Task]:
        return await self._admin.get_jira_tasks(mode)

    async def get_github_stats(
        self,
        since_date: datetime | None,
        only_contributed: bool,
        org_name: str,
    ) -> list[RepoCommitStat] | None:
        return await self._admin.get_github_stats(since_date, only_contributed, org_name)

    def get_wifi_location(self) -> str | None:
        return self.task_manager.get_wifi_location()

    # ── PR ────────────────────────────────────────────────────────────────────

    async def list_prs(self) -> list[PullRequest]:
        return await self._pr.list_prs()

    async def sync_prs(self, date: datetime) -> int:
        return await self._pr.sync_prs(date)

    async def run_ai_prompt(self, prompt: str) -> str:
        return await self._admin.run_ai_prompt(prompt)

    # ── Feedback ──────────────────────────────────────────────────────────────

    def add_feedback_received(self, text: str, from_person: str, context: str, date: datetime) -> None:
        if self._feedback:
            self._feedback.add_received(text, from_person, context, date)

    def add_feedback_given(self, text: str, to_person: str, context: str, date: datetime) -> None:
        if self._feedback:
            self._feedback.add_given(text, to_person, context, date)

    def list_feedback(
        self,
        year: int,
        quarter: int | None = None,
        person: str | None = None,
        feedback_type: str | None = None,
    ) -> list[dict[str, object]]:
        if not self._feedback:
            return []
        return self._feedback.list_feedback(year, quarter=quarter, person=person, feedback_type=feedback_type)

    # ── Screen Time ───────────────────────────────────────────────────────────

    def get_screen_time(self, date: datetime) -> list[tuple[str, int]]:
        if not self._screen_time:
            return []
        return self._screen_time.get_usage(date)

    def get_screen_time_formatted(self, date: datetime) -> str:
        if not self._screen_time:
            return ""
        return self._screen_time.format_usage(date)
