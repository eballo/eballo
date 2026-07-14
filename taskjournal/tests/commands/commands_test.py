from datetime import datetime, timedelta
from os.path import join
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pytest import mark, raises
from pytest_mock import MockerFixture

from taskjournal.commands.commands import CommandManager
from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Status, Task
from taskjournal.repositories.task_formatter import TaskFormatter


class TestCommands:

    def test__get_week_folder__creates_dir_and_returns_path(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        cmd.file_service.get_week_folder.return_value = temp_week_folder
        makedirs = mocker.patch("taskjournal.commands.daily.makedirs")

        # when
        result = cmd._get_week_folder(fixed_datetime)

        # then
        assert result == temp_week_folder
        cmd.file_service.get_week_folder.assert_called_once()
        makedirs.assert_called_once_with(temp_week_folder, exist_ok=True)

    def test__get_daily_notes_file_path__joins_week_folder_and_filename(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        mocker.patch.object(cmd._daily, "_get_week_folder", return_value=temp_week_folder)
        cmd.time_service.get_daily_notes_name.return_value = "2025-01-15-DailyNotes.md"

        # when
        path = cmd._get_daily_notes_file_path(fixed_datetime)

        # then
        assert path.endswith(join("week3", "2025-01-15-DailyNotes.md"))
        cmd.time_service.get_daily_notes_name.assert_called_once_with(fixed_datetime)

    @mark.asyncio
    async def test_create_daily_notes__skips_when_file_exists_and_not_forced(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        mocker.patch.object(
            cmd._daily,
            "_get_daily_notes_file_path",
            return_value=join(temp_week_folder, "2025-01-15-DailyNotes.md"),
        )
        cmd.file_service.load_template.return_value = "date={{date}}, time={{time}}, sprint={{sprint_name}}"
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        warn = mocker.patch("taskjournal.commands.daily.logger.warning")

        mocker.patch.object(
            cmd.github,
            "update_status_if_task_reviewed",
            new_callable=AsyncMock,
            return_value=[],
        )

        # when
        await cmd.create_daily_notes(fixed_datetime, force=False)

        # then
        warn.assert_called_once()
        cmd.task_formatter.format_tasks.assert_not_called()

    @mark.asyncio
    async def test_create_daily_notes__creates_when_forced_even_if_exists(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        path = join(temp_week_folder, "2025-01-15-DailyNotes.md")
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value=path)
        cmd.file_service.load_template.return_value = "date={{date}}, time={{time}}, sprint={{sprint_name}}\n{{tasks}}\n{{code_review_tasks}}"
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        cmd.task_manager.get_default_tasks.return_value = ["task-default"]
        mocker.patch.object(
            cmd.jira,
            "get_current_sprint_tasks_not_done_assigned_to_me",
            new_callable=AsyncMock,
            return_value=["task-jira-pending"],
        )
        mocker.patch.object(
            cmd.jira,
            "get_current_sprint_tasks_in_code_review",
            new_callable=AsyncMock,
            return_value=["task-code-review"],
        )
        cmd.task_manager.get_previous_pending_tasks.return_value = ["task-prev"]
        mocker.patch(
            "taskjournal.services.task_manager.TaskManager.unique_tasks",
            return_value=["task-default", "task-prev", "task-jira-pending"],
        )
        mocker.patch(
            "taskjournal.services.task_manager.TaskManager.get_unique_epic_names",
            return_value=[],
        )
        # Use SimpleNamespace to provide a .name attribute without conflicting with MagicMock's 'name' kwarg
        mocker.patch.object(
            cmd.jira,
            "get_active_sprint",
            return_value=SimpleNamespace(name="Sprint 42"),
        )
        mocker.patch.object(
            cmd.github,
            "update_status_if_task_reviewed",
            new_callable=AsyncMock,
            return_value=["task-code-review"],
        )
        mocker.patch.object(cmd._daily, "_schedule_macos_alarm")
        cp = mocker.patch("taskjournal.commands.daily.console.print")

        # when
        await cmd.create_daily_notes(fixed_datetime, force=True)

        # then
        cmd.file_service.write_to_file.assert_called_once()
        assert cmd.task_formatter.format_tasks.call_count == 2
        assert any(
            "estimated finish" in " ".join(map(str, c.args))
            for c in cp.mock_calls
        )

    @mark.asyncio
    async def test_create_daily_notes__uses_fallback_sprint_name_when_no_active_sprint(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        mocker.patch.object(
            cmd._daily,
            "_get_daily_notes_file_path",
            return_value=join(temp_week_folder, "2025-01-15-DailyNotes.md"),
        )
        cmd.file_service.load_template.return_value = "sprint={{sprint_name}}\n{{tasks}}\n{{code_review_tasks}}"
        mocker.patch("taskjournal.commands.daily.exists", return_value=False)
        mocker.patch.object(cmd.jira, "get_active_sprint", return_value=None)
        cmd.task_manager.get_default_tasks.return_value = []
        mocker.patch.object(
            cmd.jira,
            "get_current_sprint_tasks_not_done_assigned_to_me",
            new_callable=AsyncMock,
            return_value=[],
        )
        mocker.patch.object(
            cmd.jira,
            "get_current_sprint_tasks_in_code_review",
            new_callable=AsyncMock,
            return_value=[],
        )
        mocker.patch.object(
            cmd.github,
            "update_status_if_task_reviewed",
            new_callable=AsyncMock,
            return_value=[],
        )
        cmd.task_manager.get_previous_pending_tasks.return_value = []
        mocker.patch(
            "taskjournal.services.task_manager.TaskManager.unique_tasks",
            return_value=[],
        )
        mocker.patch.object(cmd._daily, "_schedule_macos_alarm")

        # when
        await cmd.create_daily_notes(fixed_datetime)

        args, _ = cmd.file_service.write_to_file.call_args
        content: str = args[1]
        # then
        assert "No active sprint" in content

    @mark.asyncio
    async def test_finalize_daily_notes__errors_when_file_missing(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        mocker.patch.object(
            cmd._daily,
            "_get_daily_notes_file_path",
            return_value=join(temp_week_folder, "missing.md"),
        )
        mocker.patch("taskjournal.commands.daily.exists", return_value=False)
        err = mocker.patch("taskjournal.commands.daily.logger.error")

        # when
        await cmd.finalize_daily_notes(fixed_datetime)

        # then
        err.assert_called_once()

    @mark.asyncio
    async def test_finalize_daily_notes__writes_end_and_spent_time_with_custom_date(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        path = join(temp_week_folder, "2025-01-15-DailyNotes.md")
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value=path)
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        cmd.file_service.check_finalized_in_file.return_value = False
        content = ["## 2025-01-15 09:30\n", "Other line\n"]
        cmd.file_service.get_lines.return_value = list(content)
        cmd.time_service.get_start_time.return_value = (0, fixed_datetime)
        cmd.time_service.get_total_time_spent.return_value = (2, 15)
        wrap = mocker.patch(
            "taskjournal.services.utils.FormatUtils.wrap_with_format",
            side_effect=lambda s: f"**{s}**",
        )
        cp = mocker.patch("taskjournal.commands.daily.console.print")
        mocker.patch.object(cmd._daily, "_cancel_macos_alarm")
        mocker.patch.object(cmd._daily, "_generate_and_write_summary", new=AsyncMock())
        custom_end = fixed_datetime + timedelta(hours=2, minutes=15)

        # when
        await cmd.finalize_daily_notes(custom_end)

        # then
        cmd.file_service.write_lines_to_file.assert_called_once()
        assert wrap.call_count >= 2
        assert any(
            "Daily notes finalized" in " ".join(map(str, c.args))
            for c in cp.mock_calls
        )

    @mark.asyncio
    async def test_finalize_daily_notes__uses_now_when_no_custom_date(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        path = join(temp_week_folder, "2025-01-15-DailyNotes.md")
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value=path)
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        mocker.patch(
            "taskjournal.services.file.FileService.check_finalized_in_file",
            return_value=False,
        )
        cmd.file_service.get_lines.return_value = ["start\n"]
        cmd.time_service.get_start_time.return_value = (0, fixed_datetime)
        mocker.patch(
            "taskjournal.services.utils.FormatUtils.wrap_with_format",
            side_effect=lambda s: f"[{s}]",
        )
        # Assumption: patch datetime.now via module-level reference
        mocker.patch(
            "taskjournal.commands.daily.datetime",
            **{
                "now.return_value": fixed_datetime + timedelta(hours=1),
                "strftime": datetime.strftime,
            },
        )
        mocker.patch.object(cmd._daily, "_cancel_macos_alarm")
        mocker.patch.object(cmd._daily, "_generate_and_write_summary", new=AsyncMock())

        # when
        await cmd.finalize_daily_notes(custom_date=None)  # type: ignore[arg-type]

    def test_daily_time__calculates_when_file_exists(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        # given
        path = "/tmp/week3/2025-01-15-DailyNotes.md"
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value=path)
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        calc = mocker.patch.object(cmd._daily, "_calculate_time")

        # when
        cmd.daily_time(fixed_datetime)

        # then
        calc.assert_called_once_with(path)

    def test_daily_time__warns_when_missing(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        # given
        mocker.patch.object(
            cmd._daily, "_get_daily_notes_file_path", return_value="/missing.md"
        )
        mocker.patch("taskjournal.commands.daily.exists", return_value=False)
        warn = mocker.patch("taskjournal.commands.daily.logger.warning")

        # when
        cmd.daily_time(fixed_datetime)

        # then
        warn.assert_called_once()

    @mark.asyncio
    async def test_create_week_summary__aggregates_total_time_stats_and_summary(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        mocker.patch.object(cmd._reports, "_get_week_folder", return_value=temp_week_folder)
        cmd.file_service.load_template.return_value = "start={{start_date}}\nend={{end_date}}\nt={{total_time}}\nworked={{total_worked_days}}\nvacation={{vacation_days}}\noffice={{days_at_office}}\nhome={{days_at_home}}\nfireman={{is_fireman_week}}\n{{summary}}"

        files = ["2025-01-13-DailyNotes.md", "2025-01-14-DailyNotes.md"]
        mocker.patch("taskjournal.commands.reports.listdir", return_value=files)

        cmd.file_service.get_summary_from_daily_notes.side_effect = ["Summary 1", "Summary 2"]

        mock_stats = {
            "start_date": fixed_datetime - timedelta(days=fixed_datetime.weekday()),
            "end_date": fixed_datetime
            - timedelta(days=fixed_datetime.weekday())
            + timedelta(days=4),
            "total_time_seconds": 5400,  # 1h 30m
            "total_worked_days": 2,
            "vacation_days": 3,
            "days_at_office": 1,
            "days_at_home": 1,
        }
        mocker.patch(
            "taskjournal.services.calendar.working_days.WorkingDaysService.get_week_stats",
            return_value=mock_stats,
        )

        mocker.patch(
            "taskjournal.services.calendar.fireman.FiremanService.is_fireman_week",
            return_value=False,
        )

        async def fake_summarize(
            summaries: list[str], stats: dict = None, is_fireman_week: bool = False
        ) -> str:
            if stats == mock_stats and not is_fireman_week:
                return "AI Weekly Summary"
            return "Failed summary"

        mocker.patch.object(cmd.ai_service, "summarize", side_effect=fake_summarize)

        cmd.time_service.seconds_to_hours_minutes.return_value = (1, 30)

        await cmd.create_week_summary(fixed_datetime)

        # then
        args, _ = cmd.file_service.write_to_file.call_args
        content: str = args[1]

        # Verify total time calculation
        assert " 1 hours and 30 minutes" in content
        # Verify AI summary was inserted
        assert "AI Weekly Summary" in content
        # Verify stats
        assert "worked=2" in content
        # Mon-Fri = 5 days. 2 worked -> 3 vacation
        assert "vacation=3" in content
        assert "office=1" in content
        assert "home=1" in content
        assert "fireman=No" in content
        assert "start=2025-01-13" in content
        assert "end=2025-01-17" in content

    @mark.asyncio
    async def test_recreate_week_summaries__calls_create_week_summary_for_each_week(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
    ) -> None:
        # given
        create_week_summary = mocker.patch.object(
            cmd._reports, "create_week_summary", new_callable=AsyncMock
        )
        start_date = datetime(2025, 1, 1)  # Wednesday (Week 1)
        end_date = datetime(2025, 1, 15)  # Wednesday (Week 3)

        # when
        await cmd.recreate_week_summaries(start_date, end_date)

        # then
        # start_date 2025-01-01 is Wednesday. Monday is 2024-12-30.
        # Week 1: starts 2024-12-30
        # Week 2: starts 2025-01-06
        # Week 3: starts 2025-01-13
        assert create_week_summary.call_count == 3
        create_week_summary.assert_has_awaits(
            [
                mocker.call(datetime(2024, 12, 30)),
                mocker.call(datetime(2025, 1, 6)),
                mocker.call(datetime(2025, 1, 13)),
            ]
        )

    @mark.asyncio
    async def test_create_half_year_review__writes_counts_and_lists(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        mocker.patch.object(cmd._reports, "_get_week_folder", return_value=temp_week_folder)
        cmd.file_service.load_template.return_value = "tasks={{total_tasks}}, epics={{total_epics}}, gh={{github_contributions}}\n{{tasks}}\n{{epics}}"
        # when
        tasks = ["T-1", "T-2", "T-3"]
        mocker.patch.object(
            cmd.jira,
            "get_current_tasks_assigned_to_me_last_6_months",
            new_callable=AsyncMock,
            return_value=tasks,
        )

        mocker.patch(
            "taskjournal.services.task_manager.TaskManager.get_unique_epics",
            return_value=["E-1", "E-2"],
        )
        mocker.patch.object(
            cmd.github,
            "get_contributions_last_6_months",
            new_callable=AsyncMock,
            return_value=123,
        )
        await cmd.create_half_year_review(fixed_datetime)

        content: str = cmd.file_service.write_to_file.call_args[0][1]
        # then
        assert "tasks=3" in content and "epics=2" in content and "gh=123" in content

    @mark.asyncio
    async def test_create_month_review__writes_counts_and_lists(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        mocker.patch.object(cmd._reports, "_get_week_folder", return_value=temp_week_folder)
        cmd.file_service.load_template.return_value = "tasks={{total_tasks}}, epics={{total_epics}}, gh={{github_contributions}}, summary={{summary}}, time={{total_time}}"
        mocker.patch.object(
            cmd.jira,
            "get_current_tasks_assigned_to_me_last_month",
            new_callable=AsyncMock,
            return_value=["M-1"],
        )
        mocker.patch(
            "taskjournal.services.task_manager.TaskManager.get_unique_epics",
            return_value=["ME-1"],
        )
        mocker.patch.object(
            cmd.github,
            "get_contributions_last_month",
            new_callable=AsyncMock,
            return_value=7,
        )

        mock_stats = {
            "start_date": datetime(2025, 1, 1),
            "end_date": datetime(2025, 1, 31),
            "total_time_seconds": 3600,
            "total_worked_days": 20,
            "vacation_days": 2,
            "days_at_office": 10,
            "days_at_home": 10,
            "daily_summaries": ["Done something"],
        }
        mocker.patch(
            "taskjournal.services.calendar.working_days.WorkingDaysService.get_month_stats",
            return_value=mock_stats,
        )

        mocker.patch.object(
            cmd.ai_service,
            "summarize",
            new_callable=AsyncMock,
            return_value="AI Month Summary",
        )
        cmd.time_service.seconds_to_hours_minutes.return_value = (1, 0)

        # when
        await cmd.create_month_review(fixed_datetime)

        content: str = cmd.file_service.write_to_file.call_args[0][1]
        # then
        assert "tasks=1" in content
        assert "epics=1" in content
        assert "gh=7" in content
        assert "summary=AI Month Summary" in content
        assert "time=1h 0m" in content
        assert "fireman" not in content.lower()
        assert "completed" not in content.lower()

    def test_create_retro__creates_when_missing_and_injects_sprint_name(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        mocker.patch.object(cmd._reports, "_get_week_folder", return_value=temp_week_folder)
        mocker.patch("taskjournal.commands.reports.exists", return_value=False)
        cmd.file_service.load_template.return_value = "retro {{sprint_name}}"
        # Use SimpleNamespace here too to avoid MagicMock 'name' kwarg conflict
        mocker.patch.object(
            cmd.jira, "get_active_sprint", return_value=SimpleNamespace(name="Alpha")
        )
        cmd.create_retro(fixed_datetime)

        # when
        content: str = cmd.file_service.write_to_file.call_args[0][1]
        # then
        assert "Alpha" in content

    def test_create_retro__noop_when_file_exists(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        mocker.patch.object(cmd._reports, "_get_week_folder", return_value=temp_week_folder)
        mocker.patch("taskjournal.commands.reports.exists", return_value=True)
        # when
        cmd.create_retro(fixed_datetime)

        # then
        cmd.file_service.write_to_file.assert_not_called()

    def test_create_backup__logs_backup_path(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        # given
        cmd.backup_service.create.return_value = "/tmp/backup.zip"
        cp = mocker.patch("taskjournal.commands.admin.console.print")

        # when
        cmd.create_backup()

        # then
        assert any(
            "Backup created at: /tmp/backup.zip" in " ".join(map(str, c.args))
            for c in cp.mock_calls
        )

    def test__calculate_time__logs_when_elapsed_available(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        # given
        cmd.time_service.calculate_working_hours.return_value = ("09:00", 3.5, datetime(2025, 1, 15, 12, 30))
        cp = mocker.patch("taskjournal.commands.daily.console.print")

        # when
        cmd._calculate_time("/tmp/day.md")

        # then
        assert cp.call_count == 3

    def test__calculate_time__logs_error_when_elapsed_missing(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        # given
        cmd.time_service.calculate_working_hours.return_value = (None, None, None)
        err = mocker.patch("taskjournal.commands.daily.logger.error")

        # when
        cmd._calculate_time("/tmp/day.md")

        # then
        err.assert_called_once()

    def test_show_info__logs_day_and_week(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        # given
        cp = mocker.patch("taskjournal.commands.admin.console.print")

        # when
        cmd.show_info(fixed_datetime)

        # then
        # fixed_datetime is 2025-01-15 (Wednesday)
        # 2025-01-15 is ISO week 3
        assert cp.call_count == 2
        calls = [c.args[0] for c in cp.mock_calls]
        assert "Today is Wednesday, 2025-01-15" in calls[0]
        assert "We are in week 3" in calls[1]

    # ── list / add / update task in daily ────────────────────────────────────

    def test_list_tasks_in_daily__returns_empty_when_file_missing(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._tasks, "_get_daily_notes_file_path", return_value="/missing.md")
        mocker.patch("taskjournal.commands.tasks.exists", return_value=False)

        result = cmd.list_tasks_in_daily(fixed_datetime)

        assert result == []

    def test_list_tasks_in_daily__returns_tasks_from_parser(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._tasks, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.tasks.exists", return_value=True)
        task = Task(id="1", description="Do it", status=Status.TODO)
        cmd.parser.parse.return_value = ParsedNote(planned_tasks=[task])

        result = cmd.list_tasks_in_daily(fixed_datetime)

        assert result == [task]

    def test_add_task_to_daily__raises_when_file_missing(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._tasks, "_get_daily_notes_file_path", return_value="/missing.md")
        mocker.patch("taskjournal.commands.tasks.exists", return_value=False)

        with raises(FileNotFoundError):
            cmd.add_task_to_daily(fixed_datetime, "New task")

    def test_add_task_to_daily__raises_when_section_not_found(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._tasks, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.tasks.exists", return_value=True)
        cmd.file_service.get_lines.return_value = ["Some line\n", "Another\n"]

        with raises(ValueError, match="Planned Tasks section not found"):
            cmd.add_task_to_daily(fixed_datetime, "New task")

    def test_add_task_to_daily__inserts_after_last_task(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._tasks, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.tasks.exists", return_value=True)
        lines = ["## Planned Tasks\n", " - [ ] Existing task\n", "## Notes\n"]
        cmd.file_service.get_lines.return_value = list(lines)

        cmd.add_task_to_daily(fixed_datetime, "New task")

        written = cmd.file_service.write_lines_to_file.call_args[0][1]
        assert any("New task" in ln for ln in written)

    def test_complete_task_in_daily__returns_true_when_found(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._tasks, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.tasks.exists", return_value=True)
        cmd.file_service.get_lines.return_value = [" - [ ] Do the thing\n"]

        result = cmd.complete_task_in_daily(fixed_datetime, "Do the thing")

        assert result is True
        written = cmd.file_service.write_lines_to_file.call_args[0][1]
        assert "[x]" in written[0]

    def test_block_task_in_daily__returns_false_when_not_found(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._tasks, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.tasks.exists", return_value=True)
        cmd.file_service.get_lines.return_value = [" - [ ] Something else\n"]

        result = cmd.block_task_in_daily(fixed_datetime, "nonexistent task")

        assert result is False

    # ── fix helpers ──────────────────────────────────────────────────────────

    def test_fix_end_time_and_time_spent__raises_when_end_before_start(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        cmd.file_service.get_lines.return_value = ["**Start Time:** 09:00:00\n"]
        cmd.time_service.get_start_time.return_value = (0, fixed_datetime)

        end_dt = fixed_datetime.replace(hour=8, minute=0)
        with raises(ValueError, match="must be after start time"):
            cmd.fix_end_time_and_time_spent("/day.md", end_dt)

    def test_fix_end_time_and_time_spent__writes_lines(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        content = ["**Start Time:** 09:00:00\n", "**End Time:** \n", "**Time Spent:** \n"]
        cmd.file_service.get_lines.return_value = list(content)
        cmd.time_service.get_start_time.return_value = (0, fixed_datetime)
        cmd.time_service.get_total_time_spent.return_value = (8, 0)
        mocker.patch("taskjournal.services.utils.FormatUtils.wrap_with_format", side_effect=lambda s: f"**{s}**")

        end_dt = fixed_datetime.replace(hour=18, minute=0, second=0)
        cmd.fix_end_time_and_time_spent("/day.md", end_dt)

        written = cmd.file_service.write_lines_to_file.call_args[0][1]
        assert any("18:00" in l for l in written)
        assert any("08:00" in l for l in written)

    def test_fix_time_spent_from_file__calculates_from_existing_end_time(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        content = ["**Start Time:** 09:00:00\n", "**End Time:** 18:00\n", "**Time Spent:** \n"]
        cmd.file_service.get_lines.return_value = list(content)
        cmd.time_service.get_start_time.return_value = (0, fixed_datetime)
        cmd.time_service.get_total_time_spent.return_value = (8, 0)
        mocker.patch("taskjournal.services.utils.FormatUtils.wrap_with_format", side_effect=lambda s: f"**{s}**")

        cmd.fix_time_spent_from_file("/day.md")

        written = cmd.file_service.write_lines_to_file.call_args[0][1]
        assert any("08:00" in l for l in written)

    def test_fix_summary__replaces_summary_section(
        self, cmd: CommandManager
    ) -> None:
        content = [
            "## 📋 Summary\n",
            "\n",
            "summary of the day\n",
            "\n",
            "---\n",
        ]
        cmd.file_service.get_lines.return_value = list(content)

        cmd.fix_summary("/day.md", "Reviewed PRs and fixed the parser bug.")

        written = cmd.file_service.write_lines_to_file.call_args[0][1]
        assert any("Reviewed PRs" in l for l in written)
        assert not any("summary of the day" in l for l in written)

    def test_append_ai_summary__inserts_before_separator_and_keeps_existing(
        self, cmd: CommandManager
    ) -> None:
        content = [
            "## 📋 Summary\n",
            "\n",
            "Manual summary line.\n",
            "\n",
            "---\n",
        ]
        cmd.file_service.get_lines.return_value = list(content)

        cmd._daily._append_ai_summary("/day.md", "AI generated text.")

        written = cmd.file_service.write_lines_to_file.call_args[0][1]
        assert any("Manual summary line." in l for l in written)
        assert any("AI generated text." in l for l in written)
        separator_idx = next(i for i, l in enumerate(written) if l.strip() == "---")
        ai_idx = next(i for i, l in enumerate(written) if "AI generated text." in l)
        assert ai_idx < separator_idx

    @mark.asyncio
    async def test_generate_and_write_summary__writes_when_no_existing_summary(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        cmd.parser.parse.return_value = ParsedNote(summary=[])
        cmd._daily.ai_service.summarize_day = AsyncMock(return_value="AI text.")
        fix = mocker.patch.object(cmd._daily, "fix_summary")

        await cmd._daily._generate_and_write_summary("/day.md", no_summary=False)

        fix.assert_called_once_with("/day.md", "AI text.")

    @mark.asyncio
    async def test_generate_and_write_summary__appends_when_summary_exists(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        cmd.parser.parse.return_value = ParsedNote(summary=["Existing summary."])
        cmd._daily.ai_service.summarize_day = AsyncMock(return_value="AI text.")
        append = mocker.patch.object(cmd._daily, "_append_ai_summary")

        await cmd._daily._generate_and_write_summary("/day.md", no_summary=False)

        append.assert_called_once_with("/day.md", "AI text.")

    @mark.asyncio
    async def test_generate_and_write_summary__force_replaces_existing_summary(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        cmd.parser.parse.return_value = ParsedNote(summary=["Existing summary."])
        cmd._daily.ai_service.summarize_day = AsyncMock(return_value="AI text.")
        fix = mocker.patch.object(cmd._daily, "fix_summary")
        append = mocker.patch.object(cmd._daily, "_append_ai_summary")

        await cmd._daily._generate_and_write_summary("/day.md", no_summary=False, force=True)

        fix.assert_called_once_with("/day.md", "AI text.")
        append.assert_not_called()

    @mark.asyncio
    async def test_generate_and_write_summary__skips_when_no_summary_flag(
        self, cmd: CommandManager
    ) -> None:
        await cmd._daily._generate_and_write_summary("/day.md", no_summary=True)

        cmd.parser.parse.assert_not_called()

    @mark.asyncio
    async def test_generate_and_write_summary__skips_when_ai_returns_empty(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        cmd.parser.parse.return_value = ParsedNote(summary=[])
        cmd._daily.ai_service.summarize_day = AsyncMock(return_value="")
        fix = mocker.patch.object(cmd._daily, "fix_summary")

        await cmd._daily._generate_and_write_summary("/day.md", no_summary=False)

        fix.assert_not_called()

    @mark.asyncio
    async def test_generate_and_write_summary__skips_when_parse_fails(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        cmd.parser.parse.return_value = None
        warn = mocker.patch("taskjournal.commands.daily.logger.warning")

        await cmd._daily._generate_and_write_summary("/day.md", no_summary=False)

        warn.assert_called_once()

    # ── add_note_to_daily ────────────────────────────────────────────────────

    def test_add_note_to_daily__inserts_timestamped_note(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        path = "/2026-07-02-DailyNotes.md"
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value=path)
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        content = [
            "## 📝 Notes\n",
            "\n",
            " - existing note\n",
            "\n",
            "---\n",
        ]
        cmd.file_service.get_lines.return_value = list(content)

        cmd.add_note_to_daily(fixed_datetime, "New quick note")

        written = cmd.file_service.write_lines_to_file.call_args[0][1]
        assert any("New quick note" in l for l in written)
        existing_idx = next(i for i, l in enumerate(written) if "existing note" in l)
        new_idx = next(i for i, l in enumerate(written) if "New quick note" in l)
        assert new_idx > existing_idx

    def test_add_note_to_daily__raises_when_file_missing(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/missing.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=False)

        import pytest
        with pytest.raises(FileNotFoundError):
            cmd.add_note_to_daily(fixed_datetime, "note")

    def test_add_note_to_daily__raises_when_notes_section_missing(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        cmd.file_service.get_lines.return_value = ["## Tasks\n", "- [ ] task\n"]

        import pytest
        with pytest.raises(ValueError, match="Notes section not found"):
            cmd.add_note_to_daily(fixed_datetime, "note")

    # ── _note_issues / audit ─────────────────────────────────────────────────

    def test_note_issues__returns_empty_for_complete_note(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        cmd.file_service.get_lines.return_value = ["line\n"]
        cmd.time_service.get_start_time.return_value = (0, fixed_datetime)
        cmd.file_service.check_finalized_in_file.return_value = True
        cmd.parser.parse.return_value = ParsedNote(time_spent="2h 15m", summary=["Accomplished things"])

        issues = cmd._note_issues("/day.md")

        assert issues == []

    def test_note_issues__reports_missing_start_time(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        cmd.file_service.get_lines.return_value = []
        cmd.time_service.get_start_time.side_effect = ValueError("no start")
        cmd.file_service.check_finalized_in_file.return_value = True
        cmd.parser.parse.return_value = ParsedNote(time_spent="1h", summary=["Done"])

        issues = cmd._note_issues("/day.md")

        assert "missing start time" in issues

    def test_note_issues__reports_missing_end_time_and_summary(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        cmd.file_service.get_lines.return_value = ["line\n"]
        cmd.time_service.get_start_time.return_value = (0, datetime(2025, 1, 15))
        cmd.file_service.check_finalized_in_file.return_value = False
        cmd.parser.parse.return_value = ParsedNote(time_spent="", summary=[])

        issues = cmd._note_issues("/day.md")

        assert "missing end time" in issues
        assert "missing time spent" in issues
        assert "missing summary" in issues

    def test_note_issues__reports_missing_time_spent(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        cmd.file_service.get_lines.return_value = ["line\n"]
        cmd.time_service.get_start_time.return_value = (0, datetime(2025, 1, 15))
        cmd.file_service.check_finalized_in_file.return_value = True
        cmd.parser.parse.return_value = ParsedNote(time_spent="", summary=["Done"])

        issues = cmd._note_issues("/day.md")

        assert "missing time spent" in issues

    @mark.asyncio
    async def test_create_daily_notes__warns_on_weekend(
        self, cmd: CommandManager, mocker: MockerFixture, temp_week_folder: str
    ) -> None:
        saturday = datetime(2026, 6, 27)  # weekday() == 5
        path = join(temp_week_folder, "2026-06-27-DailyNotes.md")
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value=path)
        cmd.file_service.load_template.return_value = ""
        mocker.patch("taskjournal.commands.daily.exists", return_value=False)
        mocker.patch.object(cmd._daily, "get_previous_day_issues", return_value=None)
        mocker.patch.object(cmd.jira, "get_active_sprint", return_value=None)
        mocker.patch.object(cmd.jira, "get_current_sprint_tasks_not_done_assigned_to_me", new_callable=AsyncMock, return_value=[])
        mocker.patch.object(cmd.jira, "get_current_sprint_tasks_in_code_review", new_callable=AsyncMock, return_value=[])
        mocker.patch.object(cmd.github, "update_status_if_task_reviewed", new_callable=AsyncMock, return_value=[])
        cmd.task_manager.get_previous_pending_tasks.return_value = []
        cmd.task_manager.get_default_tasks.return_value = []
        warn = mocker.patch("taskjournal.commands.daily.logger.warning")

        await cmd.create_daily_notes(saturday)

        assert any("Saturday" in str(c.args) for c in warn.mock_calls)

    def test_get_previous_day_issues__returns_issues_on_weekend(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        # Sunday — checks Saturday
        sunday = datetime(2026, 6, 28)  # weekday() == 6
        saturday_file = "/notes/2026-06-27-DailyNotes.md"
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value=saturday_file)
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        mocker.patch.object(cmd._daily, "_note_issues", return_value=["missing end time"])

        result = cmd.get_previous_day_issues(sunday)

        assert result is not None
        date_str, file_path, issues = result
        assert date_str == "2026-06-27"
        assert file_path == saturday_file
        assert "missing end time" in issues

    def test_get_previous_day_issues__returns_none_when_no_issues(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        monday = datetime(2026, 6, 22)
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/notes/friday.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        mocker.patch.object(cmd._daily, "_note_issues", return_value=[])

        result = cmd.get_previous_day_issues(monday)

        assert result is None

    def test_get_previous_day_issues__skips_missing_days_to_find_last_note(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        # User returns on Friday after Wed-Thu holiday; last note was Tuesday.
        friday = datetime(2026, 6, 26)  # weekday=4
        tuesday_file = "/notes/2026-06-23-DailyNotes.md"

        def _file_path(d: datetime) -> str:
            return f"/notes/{d.strftime('%Y-%m-%d')}-DailyNotes.md"

        def _exists(path: str) -> bool:
            return path == tuesday_file

        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", side_effect=_file_path)
        mocker.patch("taskjournal.commands.daily.exists", side_effect=_exists)
        mocker.patch.object(cmd._daily, "_note_issues", return_value=["missing end time"])

        result = cmd.get_previous_day_issues(friday)

        assert result is not None
        date_str, file_path, issues = result
        assert date_str == "2026-06-23"
        assert file_path == tuesday_file

    def test_get_previous_day_issues__returns_none_when_no_notes_in_14_days(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        today = datetime(2026, 6, 26)
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/notes/missing.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=False)

        result = cmd.get_previous_day_issues(today)

        assert result is None

    def test_audit_daily_notes__returns_empty_when_year_dir_missing(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        mocker.patch("taskjournal.commands.daily.exists", return_value=False)

        result = cmd.audit_daily_notes(2025)

        assert result == []

    def test_audit_weekly_coverage__reports_missing_days(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        year_dir = tmp_path / "2025"
        week_dir = year_dir / "week02"
        week_dir.mkdir(parents=True)
        (week_dir / "2025-01-06-DailyNotes.md").write_text("")

        mocker.patch("taskjournal.commands.daily.BASE_DIR", str(tmp_path))
        mocker.patch("taskjournal.commands.daily.TEMPLATE_FORMAT", "md")

        result = cmd.audit_weekly_coverage(2025)

        assert any("week02" == entry for entry, _ in result)
        week02_missing = next(missing for entry, missing in result if entry == "week02")
        assert "2025-01-07" in week02_missing

    def test_audit_weekly_coverage__holiday_file_counts_as_present(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        year_dir = tmp_path / "2025"
        week_dir = year_dir / "week02"
        week_dir.mkdir(parents=True)
        (week_dir / "2025-01-06-DailyNotes.md").write_text("")
        (week_dir / "2025-01-07-DailyNotes-Holidays.md").write_text("")
        (week_dir / "2025-01-08-DailyNotes.md").write_text("")
        (week_dir / "2025-01-09-DailyNotes.md").write_text("")
        (week_dir / "2025-01-10-DailyNotes.md").write_text("")

        mocker.patch("taskjournal.commands.daily.BASE_DIR", str(tmp_path))
        mocker.patch("taskjournal.commands.daily.TEMPLATE_FORMAT", "md")

        result = cmd.audit_weekly_coverage(2025)

        assert all(entry != "week02" for entry, _ in result)

    def test_audit_weekly_coverage__txt_format_respected(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        year_dir = tmp_path / "2025"
        week_dir = year_dir / "week02"
        week_dir.mkdir(parents=True)
        (week_dir / "2025-01-06-DailyNotes.txt").write_text("")
        (week_dir / "2025-01-07-DailyNotes-Holidays.txt").write_text("")
        (week_dir / "2025-01-08-DailyNotes.txt").write_text("")
        (week_dir / "2025-01-09-DailyNotes.txt").write_text("")
        (week_dir / "2025-01-10-DailyNotes.txt").write_text("")

        mocker.patch("taskjournal.commands.daily.BASE_DIR", str(tmp_path))
        mocker.patch("taskjournal.commands.daily.TEMPLATE_FORMAT", "txt")

        result = cmd.audit_weekly_coverage(2025)

        assert all(entry != "week02" for entry, _ in result)

    # ── search_notes ─────────────────────────────────────────────────────────

    def test_search_notes__returns_matching_lines(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: str
    ) -> None:
        note_dir = str(tmp_path)
        week_dir = join(note_dir, "week01")
        import os
        os.makedirs(week_dir)
        note_file = join(week_dir, "2025-01-05-DailyNotes.md")
        with open(note_file, "w") as f:
            f.write("## Planned Tasks\n[ ] Fix the bug\n[ ] Review PR\n")

        mocker.patch("taskjournal.commands.search.BASE_DIR", note_dir)
        mocker.patch("taskjournal.commands.search.TEMPLATE_FORMAT", "md")

        results = cmd.search_notes("fix")

        assert len(results) == 1
        assert "Fix the bug" in results[0][2]

    def test_search_notes__filters_by_note_type(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: str
    ) -> None:
        note_dir = str(tmp_path)
        week_dir = join(note_dir, "week01")
        import os
        os.makedirs(week_dir)
        daily = join(week_dir, "2025-01-05-DailyNotes.md")
        summary = join(week_dir, "2025-01-05-week-summary.md")
        with open(daily, "w") as f:
            f.write("[ ] Match here\n")
        with open(summary, "w") as f:
            f.write("Match here too\n")

        mocker.patch("taskjournal.commands.search.BASE_DIR", note_dir)
        mocker.patch("taskjournal.commands.search.TEMPLATE_FORMAT", "md")

        daily_results = cmd.search_notes("match", note_type="daily")
        week_results = cmd.search_notes("match", note_type="week")

        assert all("DailyNotes" in r[0] for r in daily_results)
        assert all("week-summary" in r[0] for r in week_results)

    # ── create_one_on_one ────────────────────────────────────────────────────

    def test_create_one_on_one__creates_parent_directory(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch("taskjournal.commands.reports.BASE_DIR", "/base")
        mocker.patch("taskjournal.commands.reports.exists", return_value=False)
        cmd.time_service.get_1on1_name.return_value = "2025-01-15-1on1.md"
        cmd.file_service.load_template.return_value = "template"
        makedirs_mock = mocker.patch("taskjournal.commands.reports.makedirs")

        cmd.create_one_on_one(fixed_datetime)

        makedirs_mock.assert_called_once()
        cmd.file_service.write_to_file.assert_called_once()

    def test_create_one_on_one__skips_write_when_file_exists(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch("taskjournal.commands.reports.BASE_DIR", "/base")
        mocker.patch("taskjournal.commands.reports.exists", return_value=True)
        cmd.time_service.get_1on1_name.return_value = "2025-01-15-1on1.md"

        cmd.create_one_on_one(fixed_datetime)

        cmd.file_service.write_to_file.assert_not_called()

    # ── add_topic_to_one_on_one ───────────────────────────────────────────────

    def test_add_topic_to_one_on_one__inserts_topic(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._reports, "create_one_on_one")
        mocker.patch("taskjournal.commands.reports.BASE_DIR", "/base")
        cmd.time_service.get_1on1_name.return_value = "2025-01-15-1on1.md"
        cmd.file_service.get_lines.return_value = [
            "# Proposal topics\n",
            "- existing\n",
        ]

        cmd.add_topic_to_one_on_one(fixed_datetime, "New agenda item")

        written = cmd.file_service.write_lines_to_file.call_args[0][1]
        assert any("New agenda item" in ln for ln in written)

    def test_add_topic_to_one_on_one__raises_when_section_missing(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._reports, "create_one_on_one")
        mocker.patch("taskjournal.commands.reports.BASE_DIR", "/base")
        cmd.time_service.get_1on1_name.return_value = "2025-01-15-1on1.md"
        cmd.file_service.get_lines.return_value = ["# Meeting notes\n", "Some text\n"]

        with raises(ValueError, match="Proposal topics.*not found"):
            cmd.add_topic_to_one_on_one(fixed_datetime, "topic")

    # ── get_streak_stats ──────────────────────────────────────────────────────

    def test_get_streak_stats__empty_when_no_notes(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        mocker.patch("taskjournal.commands.daily.BASE_DIR", "/empty")
        mocker.patch("taskjournal.commands.daily.walk", return_value=[])

        stats = cmd.get_streak_stats(datetime(2025, 1, 15))

        assert stats["current"] == 0
        assert stats["total"] == 0

    def test_get_streak_stats__counts_consecutive_weekdays(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        import os
        mocker.patch("taskjournal.commands.daily.BASE_DIR", "/notes")
        files = [
            "2025-01-13-DailyNotes.md",  # Mon
            "2025-01-14-DailyNotes.md",  # Tue
            "2025-01-15-DailyNotes.md",  # Wed (today)
        ]
        mocker.patch(
            "taskjournal.commands.daily.walk",
            return_value=[("/notes/w03", [], files)],
        )

        stats = cmd.get_streak_stats(datetime(2025, 1, 15))

        assert stats["current"] == 3
        assert stats["total"] == 3

    # ── sync_daily_notes ──────────────────────────────────────────────────────

    @mark.asyncio
    async def test_sync_daily_notes__raises_when_file_missing(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/missing.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=False)

        with raises(FileNotFoundError):
            await cmd.sync_daily_notes(fixed_datetime)

    @mark.asyncio
    async def test_sync_daily_notes__skips_write_when_all_tasks_present(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        existing = Task(id="1", description="Fix bug", status=Status.TODO)
        cmd.parser.parse.return_value = ParsedNote(planned_tasks=[existing])
        pending = Task(id="1", description="Fix bug", status=Status.TODO)
        cmd.jira.get_current_sprint_tasks_not_done_assigned_to_me = AsyncMock(return_value=[pending])
        cmd.jira.get_current_sprint_tasks_in_code_review = AsyncMock(return_value=[])
        cmd.github.update_status_if_task_reviewed = AsyncMock()

        await cmd.sync_daily_notes(fixed_datetime)

        cmd.file_service.write_lines_to_file.assert_not_called()

    # ── sync_tasks ────────────────────────────────────────────────────────────

    @mark.asyncio
    async def test_sync_tasks__raises_when_file_missing(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/missing.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=False)

        with raises(FileNotFoundError):
            await cmd.sync_tasks(fixed_datetime)

    @mark.asyncio
    async def test_sync_tasks__adds_missing_and_corrects_stale_status(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)

        real_formatter = TaskFormatter()
        cmd.task_formatter.status_checkbox_char.side_effect = TaskFormatter.status_checkbox_char
        cmd.task_formatter.format_task.side_effect = (
            lambda task, with_name, with_status: real_formatter.format_task(task, with_name, with_status)
        )

        lines = [
            "## Planned Tasks\n",
            " - [ ] [JIRA-2]Old but unrelated\n",
            "## Code Review Tasks\n",
            " - [~] [JIRA-3]Review PR that got approved\n",
        ]
        cmd.file_service.get_lines.return_value = list(lines)

        # JIRA-1 is a new active task, not yet present anywhere in the notes
        active_task = Task(id="1", key="JIRA-1", description="New active task", status=Status.IN_PROGRESS)
        # JIRA-3 is already present in Code Review Tasks but was just approved (should flip to done)
        code_review_task = Task(id="3", key="JIRA-3", description="Review PR that got approved", status=Status.DONE)

        cmd.jira.get_current_sprint_tasks_not_done_assigned_to_me = AsyncMock(return_value=[active_task])
        cmd.jira.get_current_sprint_tasks_in_code_review = AsyncMock(return_value=[code_review_task])
        cmd.github.update_status_if_task_reviewed = AsyncMock()

        added, updated = await cmd.sync_tasks(fixed_datetime)

        assert added == 1
        assert updated == 1
        written_lines = cmd.file_service.write_lines_to_file.call_args[0][1]
        assert any("JIRA-1" in line and "[>]" in line for line in written_lines)
        assert any("JIRA-3" in line and "[x]" in line for line in written_lines)

    @mark.asyncio
    async def test_sync_tasks__corrects_merged_pr_no_longer_returned_by_jira(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        # given: the Jira ticket already moved past "Code Review" (e.g. the
        # author moved it to Done right after merging), so it's no longer in
        # either live Jira query — but the daily note still lists it as
        # pending review and its PR link shows it's actually merged.
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)

        lines = [
            "## Code Review Tasks\n",
            " - [ ] [BE-3171](https://jira/browse/BE-3171)"
            "[🐙](https://github.com/acme/albedo/pull/1918)[albedo] Improve apidocs load - Gerard Solé\n",
        ]
        cmd.file_service.get_lines.return_value = list(lines)

        cmd.jira.get_current_sprint_tasks_not_done_assigned_to_me = AsyncMock(return_value=[])
        cmd.jira.get_current_sprint_tasks_in_code_review = AsyncMock(return_value=[])
        cmd.github.update_status_if_task_reviewed = AsyncMock()
        cmd.github.has_user_approved_pr = AsyncMock(return_value=True)

        added, updated = await cmd.sync_tasks(fixed_datetime)

        assert added == 0
        assert updated == 1
        cmd.github.has_user_approved_pr.assert_awaited_once_with(
            "https://github.com/acme/albedo/pull/1918"
        )
        written_lines = cmd.file_service.write_lines_to_file.call_args[0][1]
        assert any("BE-3171" in line and line.startswith(" - [x]") for line in written_lines)

    @mark.asyncio
    async def test_sync_tasks__skips_write_when_everything_in_sync(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        cmd.task_formatter.status_checkbox_char.side_effect = TaskFormatter.status_checkbox_char

        cmd.file_service.get_lines.return_value = [
            "## Planned Tasks\n",
            " - [>] [JIRA-1]Already tracked\n",
        ]
        active_task = Task(id="1", key="JIRA-1", description="Already tracked", status=Status.IN_PROGRESS)
        cmd.jira.get_current_sprint_tasks_not_done_assigned_to_me = AsyncMock(return_value=[active_task])
        cmd.jira.get_current_sprint_tasks_in_code_review = AsyncMock(return_value=[])
        cmd.github.update_status_if_task_reviewed = AsyncMock()

        added, updated = await cmd.sync_tasks(fixed_datetime)

        assert (added, updated) == (0, 0)
        cmd.file_service.write_lines_to_file.assert_not_called()

    # ── _schedule_macos_alarm ─────────────────────────────────────────────────

    def test__schedule_macos_alarm__skips_on_non_darwin(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.daily.platform", "linux")
        run = mocker.patch("taskjournal.commands.daily.subprocess_run")

        cmd._schedule_macos_alarm(fixed_datetime, str(tmp_path / ".alarm_job"))

        run.assert_not_called()

    def test__schedule_macos_alarm__logs_info_and_saves_job_on_success(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.daily.platform", "darwin")
        fake_result = mocker.MagicMock()
        fake_result.returncode = 0
        mocker.patch("taskjournal.commands.daily.subprocess_run", return_value=fake_result)
        cp = mocker.patch("taskjournal.commands.daily.console.print")
        alarm_file = str(tmp_path / ".alarm_job")

        cmd._schedule_macos_alarm(fixed_datetime, alarm_file)

        assert any("Alarm set for" in str(c.args) for c in cp.mock_calls)
        assert Path(alarm_file).read_text() == "reminder|2025-01-15|09:30|Time to wrap up!"

    def test__schedule_macos_alarm__logs_debug_on_failure(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.daily.platform", "darwin")
        fake_result = mocker.MagicMock()
        fake_result.returncode = 1
        fake_result.stderr = b"Reminders not available"
        mocker.patch("taskjournal.commands.daily.subprocess_run", return_value=fake_result)
        debug = mocker.patch("taskjournal.commands.daily.logger.debug")

        cmd._schedule_macos_alarm(fixed_datetime, str(tmp_path / ".alarm_job"))

        assert any("Could not create reminder" in str(c.args) for c in debug.mock_calls)

    def test__schedule_macos_alarm__logs_debug_on_exception(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.daily.platform", "darwin")
        mocker.patch(
            "taskjournal.commands.daily.subprocess_run",
            side_effect=FileNotFoundError("at not found"),
        )
        debug = mocker.patch("taskjournal.commands.daily.logger.debug")

        cmd._schedule_macos_alarm(fixed_datetime, str(tmp_path / ".alarm_job"))

        assert any("Could not schedule alarm" in str(c.args) for c in debug.mock_calls)

    # ── _cancel_macos_alarm ───────────────────────────────────────────────────

    def test__cancel_macos_alarm__skips_on_non_darwin(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.daily.platform", "linux")
        run = mocker.patch("taskjournal.commands.daily.subprocess_run")
        alarm_file = tmp_path / ".alarm_job"
        alarm_file.write_text("42")

        cmd._cancel_macos_alarm(str(alarm_file))

        run.assert_not_called()

    def test__cancel_macos_alarm__skips_when_no_alarm_file(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.daily.platform", "darwin")
        run = mocker.patch("taskjournal.commands.daily.subprocess_run")

        cmd._cancel_macos_alarm(str(tmp_path / ".alarm_job"))

        run.assert_not_called()

    def test__cancel_macos_alarm__cancels_reminder_and_removes_file(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.daily.platform", "darwin")
        fake_result = mocker.MagicMock()
        fake_result.returncode = 0
        run = mocker.patch("taskjournal.commands.daily.subprocess_run", return_value=fake_result)
        cp = mocker.patch("taskjournal.commands.daily.console.print")
        alarm_file = tmp_path / ".alarm_job"
        alarm_file.write_text("reminder|2025-01-15|09:30|Time to wrap up!")

        cmd._cancel_macos_alarm(str(alarm_file))

        run.assert_called_once_with(
            ["osascript", "-e", mocker.ANY], capture_output=True, timeout=10
        )
        assert not alarm_file.exists()
        assert any("Alarm cancelled" in str(c.args) for c in cp.mock_calls)

    def test__cancel_macos_alarm__logs_debug_on_exception(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.daily.platform", "darwin")
        mocker.patch(
            "taskjournal.commands.daily.subprocess_run",
            side_effect=RuntimeError("osascript failed"),
        )
        debug = mocker.patch("taskjournal.commands.daily.logger.debug")
        alarm_file = tmp_path / ".alarm_job"
        alarm_file.write_text("reminder|2025-01-15|09:30|Time to wrap up!")

        cmd._cancel_macos_alarm(str(alarm_file))

        assert any("Could not cancel alarm" in str(c.args) for c in debug.mock_calls)

    # ── get_standup ───────────────────────────────────────────────────────────

    def test_get_standup__returns_done_planned_and_code_review_from_yesterday(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/fake/file.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        cmd.parser.parse.return_value = ParsedNote(
            planned_tasks=[Task(id="1", description="Fix bug", status=Status.DONE)],
            code_review_tasks=[Task(id="2", description="Review PR #42", status=Status.DONE)],
        )
        result = cmd._daily.get_standup(fixed_datetime)
        assert "Fix bug" in result["done"]
        assert "Review PR #42" in result["done"]

    def test_get_standup__returns_done_today_separately(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/fake/file.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        cmd.parser.parse.return_value = ParsedNote(
            planned_tasks=[
                Task(id="1", description="Deploy hotfix", status=Status.DONE),
                Task(id="2", description="Write docs", status=Status.TODO),
            ],
            code_review_tasks=[Task(id="3", description="Review PR #99", status=Status.DONE)],
        )
        result = cmd._daily.get_standup(fixed_datetime)
        assert "Deploy hotfix" in result["today_done"]
        assert "Review PR #99" in result["today_done"]
        assert "Write docs" in result["today"]

    def test_get_standup__returns_blockers_from_both_sections(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/fake/file.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=True)
        cmd.parser.parse.return_value = ParsedNote(
            planned_tasks=[Task(id="1", description="Waiting on API", status=Status.BLOCKED)],
            code_review_tasks=[Task(id="2", description="PR blocked by CI", status=Status.BLOCKED)],
        )
        result = cmd._daily.get_standup(fixed_datetime)
        assert "Waiting on API" in result["blockers"]
        assert "PR blocked by CI" in result["blockers"]

    def test_get_standup__returns_empty_when_files_missing(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._daily, "_get_daily_notes_file_path", return_value="/fake/file.md")
        mocker.patch("taskjournal.commands.daily.exists", return_value=False)
        result = cmd._daily.get_standup(fixed_datetime)
        assert result == {"done": [], "today_done": [], "today": [], "blockers": []}

    # ── Delegation wrappers ───────────────────────────────────────────────────

    def test_get_standup__delegates_to_daily(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        expected = {"done": ["task"], "today_done": [], "today": [], "blockers": []}
        mocker.patch.object(cmd._daily, "get_standup", return_value=expected)
        assert cmd.get_standup(fixed_datetime) == expected

    def test_add_recurring_task__delegates_to_recurring(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        add = mocker.patch.object(cmd._recurring, "add")
        cmd.add_recurring_task("standup", ["monday"], monthly=False)
        add.assert_called_once_with("standup", ["monday"], False)

    def test_remove_recurring_task__delegates_to_recurring(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(cmd._recurring, "remove", return_value=True)
        assert cmd.remove_recurring_task("standup") is True

    def test_list_recurring_tasks__delegates_to_recurring(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        tasks = [{"description": "standup", "days": "every"}]
        mocker.patch.object(cmd._recurring, "list_all", return_value=tasks)
        assert cmd.list_recurring_tasks() == tasks

    def test_get_completion_stats__delegates(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        data = [("2025-01-01", 5, 6)]
        mocker.patch.object(cmd._daily, "get_completion_stats", return_value=data)
        assert cmd.get_completion_stats(2025) == data

    def test_get_workload_stats__delegates(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        data = [("W01", 3600)]
        mocker.patch.object(cmd._daily, "get_workload_stats", return_value=data)
        assert cmd.get_workload_stats(2025) == data

    def test_get_pattern_stats__delegates(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        data: dict[str, object] = {"best_day": "Monday", "carry_over_rate": 10}
        mocker.patch.object(cmd._daily, "get_pattern_stats", return_value=data)
        assert cmd.get_pattern_stats(2025) == data

    def test_get_tags_stats__delegates(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        data = [("Platform", 5)]
        mocker.patch.object(cmd._daily, "get_tags_stats", return_value=data)
        assert cmd.get_tags_stats(2025) == data

    def test_count_week_folders__delegates(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(cmd._daily, "count_week_folders", return_value=42)
        assert cmd.count_week_folders(2025) == 42

    def test_wip_task_in_daily__delegates(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._tasks, "wip_task_in_daily", return_value=True)
        assert cmd.wip_task_in_daily(fixed_datetime, "my task") is True

    def test_schedule_backup__delegates(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        install = mocker.patch.object(cmd.schedule_service, "install")
        cp = mocker.patch("taskjournal.commands.admin.console.print")
        cmd.schedule_backup(17, 30)
        install.assert_called_once_with(17, 30)

    def test_disable_backup_schedule__delegates(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        uninstall = mocker.patch.object(cmd.schedule_service, "uninstall")
        mocker.patch("taskjournal.commands.admin.console.print")
        cmd.disable_backup_schedule()
        uninstall.assert_called_once()

    @mark.asyncio
    async def test_get_jira_tasks__all_mode(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(cmd.jira, "get_current_sprint_tasks", new_callable=AsyncMock, return_value=[])
        result = await cmd.get_jira_tasks("all")
        assert result == []

    @mark.asyncio
    async def test_get_jira_tasks__mine_mode(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(cmd.jira, "get_current_sprint_tasks_all_assigned_to_me", new_callable=AsyncMock, return_value=[])
        assert await cmd.get_jira_tasks("mine") == []

    @mark.asyncio
    async def test_get_jira_tasks__code_mode(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(cmd.jira, "get_current_sprint_tasks_in_code_review", new_callable=AsyncMock, return_value=[])
        assert await cmd.get_jira_tasks("code") == []

    @mark.asyncio
    async def test_get_jira_tasks__midreview_mode(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(cmd.jira, "get_current_tasks_assigned_to_me_last_6_months", new_callable=AsyncMock, return_value=[])
        assert await cmd.get_jira_tasks("midreview") == []

    @mark.asyncio
    async def test_get_jira_tasks__month_mode(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(cmd.jira, "get_current_tasks_assigned_to_me_last_month", new_callable=AsyncMock, return_value=[])
        assert await cmd.get_jira_tasks("month") == []

    @mark.asyncio
    async def test_run_ai_prompt__delegates(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(cmd.ai_service, "summarize", new_callable=AsyncMock, return_value="AI result")
        result = await cmd.run_ai_prompt("Summarize this")
        assert result == "AI result"

    def test_list_alarms__delegates(self, cmd: CommandManager, mocker: MockerFixture) -> None:
        expected = [{"date": "2025-01-15", "job_id": "abc"}]
        mocker.patch.object(cmd._daily, "list_alarms", return_value=expected)
        result = cmd.list_alarms(weeks_back=2)
        assert result == expected
        cmd._daily.list_alarms.assert_called_once_with(2)

    def test_set_alarm__delegates(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        set_alarm = mocker.patch.object(cmd._daily, "set_alarm")
        alarm_time = fixed_datetime.replace(hour=17, minute=30)
        cmd.set_alarm(fixed_datetime, alarm_time, "Go home!")
        set_alarm.assert_called_once_with(fixed_datetime, alarm_time, "Go home!")

    def test_cancel_alarm_for_date__delegates(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd._daily, "cancel_alarm_for_date", return_value=True)
        result = cmd.cancel_alarm_for_date(fixed_datetime)
        assert result is True

    @mark.asyncio
    async def test_create_quarter_review__delegates(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        create = mocker.patch.object(
            cmd._reports, "create_quarter_review", new_callable=AsyncMock
        )
        await cmd.create_quarter_review(fixed_datetime)
        create.assert_awaited_once_with(fixed_datetime)

    @mark.asyncio
    async def test_create_year_review__delegates(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        create = mocker.patch.object(
            cmd._reports, "create_year_review", new_callable=AsyncMock
        )
        await cmd.create_year_review(fixed_datetime)
        create.assert_awaited_once_with(fixed_datetime)

    def test_compare_periods__delegates(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        expected = [{"label": "Q1 2025", "total_worked_days": 60}]
        mocker.patch.object(cmd._reports, "compare_periods", return_value=expected)
        result = cmd.compare_periods("quarter", 2025)
        assert result == expected
        cmd._reports.compare_periods.assert_called_once_with("quarter", 2025)

    def test_get_wifi_location__delegates_to_task_manager(
        self, cmd: CommandManager
    ) -> None:
        cmd.task_manager.get_wifi_location.return_value = "Home"
        result = cmd.get_wifi_location()
        assert result == "Home"

    @mark.asyncio
    async def test_list_prs__delegates(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        list_prs = mocker.patch.object(cmd._pr, "list_prs", new_callable=AsyncMock, return_value=[])
        result = await cmd.list_prs()
        assert result == []
        list_prs.assert_awaited_once()

    @mark.asyncio
    async def test_sync_prs__delegates(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        sync = mocker.patch.object(cmd._pr, "sync_prs", new_callable=AsyncMock, return_value=3)
        result = await cmd.sync_prs(fixed_datetime)
        assert result == 3
        sync.assert_awaited_once_with(fixed_datetime)

    def test_add_feedback_received__noop_when_no_feedback_service(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        cmd._feedback = None
        cmd.add_feedback_received("Great work", "Alice", "sprint review", fixed_datetime)

    def test_add_feedback_received__delegates_when_service_present(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        feedback_svc = mocker.MagicMock(name="FeedbackServiceMock")
        cmd._feedback = feedback_svc
        cmd.add_feedback_received("Great work", "Alice", "sprint review", fixed_datetime)
        feedback_svc.add_received.assert_called_once_with(
            "Great work", "Alice", "sprint review", fixed_datetime
        )

    def test_add_feedback_given__noop_when_no_feedback_service(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        cmd._feedback = None
        cmd.add_feedback_given("Keep it up", "Bob", "1on1", fixed_datetime)

    def test_add_feedback_given__delegates_when_service_present(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        feedback_svc = mocker.MagicMock(name="FeedbackServiceMock")
        cmd._feedback = feedback_svc
        cmd.add_feedback_given("Keep it up", "Bob", "1on1", fixed_datetime)
        feedback_svc.add_given.assert_called_once_with(
            "Keep it up", "Bob", "1on1", fixed_datetime
        )

    def test_list_feedback__returns_empty_when_no_service(
        self, cmd: CommandManager
    ) -> None:
        cmd._feedback = None
        result = cmd.list_feedback(2025)
        assert result == []

    def test_list_feedback__delegates_when_service_present(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        feedback_svc = mocker.MagicMock(name="FeedbackServiceMock")
        feedback_svc.list_feedback.return_value = [{"text": "Good job"}]
        cmd._feedback = feedback_svc
        result = cmd.list_feedback(2025, quarter=1, person="Alice", feedback_type="received")
        assert result == [{"text": "Good job"}]
        feedback_svc.list_feedback.assert_called_once_with(
            2025, quarter=1, person="Alice", feedback_type="received"
        )

    def test_get_screen_time__returns_empty_when_no_service(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        cmd._screen_time = None
        result = cmd.get_screen_time(fixed_datetime)
        assert result == []

    def test_get_screen_time__delegates_when_service_present(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        screen_svc = mocker.MagicMock(name="ScreenTimeServiceMock")
        screen_svc.get_usage.return_value = [("Safari", 3600)]
        cmd._screen_time = screen_svc
        result = cmd.get_screen_time(fixed_datetime)
        assert result == [("Safari", 3600)]

    def test_get_screen_time_formatted__returns_empty_when_no_service(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        cmd._screen_time = None
        result = cmd.get_screen_time_formatted(fixed_datetime)
        assert result == ""

    def test_get_screen_time_formatted__delegates_when_service_present(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        screen_svc = mocker.MagicMock(name="ScreenTimeServiceMock")
        screen_svc.format_usage.return_value = "Safari: 1h"
        cmd._screen_time = screen_svc
        result = cmd.get_screen_time_formatted(fixed_datetime)
        assert result == "Safari: 1h"

    def test_create_one_on_one__delegates(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        create = mocker.patch.object(cmd._reports, "create_one_on_one")
        cmd.create_one_on_one(fixed_datetime, person_name="Alice")
        create.assert_called_once_with(fixed_datetime, person_name="Alice")

    @mark.asyncio
    async def test_create_quarter_review__writes_stats_and_summary(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        mocker.patch.object(cmd._reports, "_get_week_folder", return_value=temp_week_folder)
        cmd.file_service.load_template.return_value = (
            "q={{quarter_num}}, year={{year}}, time={{total_time}}, "
            "worked={{total_worked_days}}, tasks={{total_tasks}}, summary={{summary}}"
        )
        mock_stats = {
            "start_date": datetime(2025, 1, 1),
            "end_date": datetime(2025, 3, 31),
            "total_time_seconds": 7200,
            "total_worked_days": 60,
            "vacation_days": 5,
            "days_at_office": 30,
            "days_at_home": 30,
            "quarter_num": 1,
            "year": 2025,
            "daily_summaries": ["Shipped feature X"],
        }
        mocker.patch(
            "taskjournal.services.calendar.working_days.WorkingDaysService.get_quarter_stats",
            return_value=mock_stats,
        )
        mocker.patch.object(
            cmd.jira,
            "get_current_tasks_assigned_to_me_last_quarter",
            new_callable=AsyncMock,
            return_value=["Q-1", "Q-2"],
        )
        mocker.patch(
            "taskjournal.services.task_manager.TaskManager.get_unique_epics",
            return_value=["QE-1"],
        )
        mocker.patch.object(
            cmd.github,
            "get_contributions_last_quarter",
            new_callable=AsyncMock,
            return_value=50,
        )
        mocker.patch.object(
            cmd.ai_service,
            "summarize",
            new_callable=AsyncMock,
            return_value="Q1 Summary",
        )
        cmd.time_service.seconds_to_hours_minutes.return_value = (2, 0)

        await cmd.create_quarter_review(fixed_datetime)

        content: str = cmd.file_service.write_to_file.call_args[0][1]
        assert "q=1" in content
        assert "year=2025" in content
        assert "tasks=2" in content
        assert "summary=Q1 Summary" in content

    @mark.asyncio
    async def test_create_year_review__writes_stats_and_summary(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        mocker.patch.object(cmd._reports, "_get_week_folder", return_value=temp_week_folder)
        cmd.file_service.load_template.return_value = (
            "year={{year}}, time={{total_time}}, worked={{total_worked_days}}, "
            "tasks={{total_tasks}}, summary={{summary}}"
        )
        mock_stats = {
            "start_date": datetime(2025, 1, 1),
            "end_date": datetime(2025, 12, 31),
            "total_time_seconds": 14400,
            "total_worked_days": 250,
            "vacation_days": 20,
            "days_at_office": 120,
            "days_at_home": 130,
            "daily_summaries": ["Year highlights"],
        }
        mocker.patch(
            "taskjournal.services.calendar.working_days.WorkingDaysService.get_year_stats",
            return_value=mock_stats,
        )
        mocker.patch.object(
            cmd.jira,
            "get_current_tasks_assigned_to_me_last_year",
            new_callable=AsyncMock,
            return_value=["Y-1"],
        )
        mocker.patch(
            "taskjournal.services.task_manager.TaskManager.get_unique_epics",
            return_value=["YE-1"],
        )
        mocker.patch.object(
            cmd.github,
            "get_contributions_last_year",
            new_callable=AsyncMock,
            return_value=300,
        )
        mocker.patch.object(
            cmd.ai_service,
            "summarize",
            new_callable=AsyncMock,
            return_value="Year Summary",
        )
        cmd.time_service.seconds_to_hours_minutes.return_value = (4, 0)

        await cmd.create_year_review(fixed_datetime)

        content: str = cmd.file_service.write_to_file.call_args[0][1]
        assert "year=2025" in content
        assert "tasks=1" in content
        assert "summary=Year Summary" in content

    def test_compare_periods_returns_quarter_stats(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
    ) -> None:
        mock_stats = {
            "total_worked_days": 60,
            "vacation_days": 5,
            "days_at_office": 30,
            "days_at_home": 30,
            "total_time_seconds": 7200,
        }
        mocker.patch(
            "taskjournal.services.calendar.working_days.WorkingDaysService.get_quarter_stats",
            return_value=mock_stats,
        )

        results = cmd.compare_periods("quarter", 2025)

        assert len(results) == 4
        assert results[0]["label"] == "Q1 2025"
        assert results[3]["label"] == "Q4 2025"
        assert results[0]["total_worked_days"] == 60

    def test_compare_periods_returns_monthly_stats(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
    ) -> None:
        mock_stats = {
            "total_worked_days": 20,
            "vacation_days": 2,
            "days_at_office": 10,
            "days_at_home": 10,
            "total_time_seconds": 3600,
        }
        mocker.patch(
            "taskjournal.services.calendar.working_days.WorkingDaysService.get_month_stats",
            return_value=mock_stats,
        )

        results = cmd.compare_periods("month", 2025)

        assert len(results) == 12
        assert "Jan 2025" in results[0]["label"]
        assert "Dec 2025" in results[11]["label"]

    def test_report_commands_note_issues_for_complete_note(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        temp_week_folder: str,
    ) -> None:
        cmd.file_service.get_lines.return_value = [
            "**Start Time:** 09:00:00\n",
            "**Date:** 2025-01-15\n",
        ]
        cmd.file_service.check_finalized_in_file.return_value = True
        note = mocker.MagicMock()
        note.time_spent = "08:00"
        note.summary = ["Work done today"]
        cmd.parser.parse.return_value = note

        issues = cmd._reports._note_issues("/fake/2025-01-15-DailyNotes.md")

        assert issues == []

    def test_report_commands_note_issues_for_incomplete_note(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
    ) -> None:
        cmd.file_service.get_lines.side_effect = FileNotFoundError("missing")
        cmd.file_service.check_finalized_in_file.return_value = False
        cmd.parser.parse.return_value = None

        issues = cmd._reports._note_issues("/fake/missing.md")

        assert "missing start time" in issues
        assert "missing end time" in issues

    def test_report_commands_warn_incomplete_week_notes(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        temp_week_folder: str,
    ) -> None:
        mocker.patch("taskjournal.commands.reports.exists", return_value=True)
        cmd.time_service.get_daily_notes_name.side_effect = (
            lambda d: f"{d.strftime('%Y-%m-%d')}-DailyNotes.md"
        )
        cmd.file_service.get_lines.side_effect = ValueError("bad")
        cmd.file_service.check_finalized_in_file.return_value = False
        cmd.parser.parse.return_value = None
        mock_logger = mocker.patch("taskjournal.commands.reports.logger")

        target = datetime(2025, 1, 15)  # Wednesday
        cmd._reports._warn_incomplete_week_notes(target, temp_week_folder)

        mock_logger.warning.assert_called()

    def test_report_commands_get_week_folder_creates_dir(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
    ) -> None:
        cmd.file_service.get_week_folder.return_value = "/fake/week"
        makedirs_mock = mocker.patch("taskjournal.commands.reports.makedirs")

        result = cmd._reports._get_week_folder(fixed_datetime)

        assert result == "/fake/week"
        makedirs_mock.assert_called_once_with("/fake/week", exist_ok=True)
