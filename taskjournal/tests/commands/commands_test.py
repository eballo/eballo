from datetime import datetime, timedelta
from os.path import join
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pytest import mark, raises
from pytest_mock import MockerFixture

from taskjournal.commands.commands import CommandManager
from taskjournal.models.task import Status, Task


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
        makedirs = mocker.patch("taskjournal.commands.commands.makedirs")

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
        mocker.patch.object(cmd, "_get_week_folder", return_value=temp_week_folder)
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
            cmd,
            "_get_daily_notes_file_path",
            return_value=join(temp_week_folder, "2025-01-15-DailyNotes.md"),
        )
        cmd.file_service.load_template.return_value = "date={{date}}, time={{time}}, sprint={{sprint_name}}"
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
        warn = mocker.patch("taskjournal.commands.commands.logger.warning")

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
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value=path)
        cmd.file_service.load_template.return_value = "date={{date}}, time={{time}}, sprint={{sprint_name}}\n{{tasks}}\n{{code_review_tasks}}"
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
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
        mocker.patch.object(cmd, "_schedule_macos_alarm")
        info = mocker.patch("taskjournal.commands.commands.logger.info")

        # when
        await cmd.create_daily_notes(fixed_datetime, force=True)

        # then
        cmd.file_service.write_to_file.assert_called_once()
        assert cmd.task_formatter.format_tasks.call_count == 2
        assert any(
            "estimated finish" in " ".join(map(str, c.args))
            for c in info.mock_calls
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
            cmd,
            "_get_daily_notes_file_path",
            return_value=join(temp_week_folder, "2025-01-15-DailyNotes.md"),
        )
        cmd.file_service.load_template.return_value = "sprint={{sprint_name}}\n{{tasks}}\n{{code_review_tasks}}"
        mocker.patch("taskjournal.commands.commands.exists", return_value=False)
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
        mocker.patch.object(cmd, "_schedule_macos_alarm")

        # when
        await cmd.create_daily_notes(fixed_datetime)

        args, _ = cmd.file_service.write_to_file.call_args
        content: str = args[1]
        # then
        assert "No active sprint" in content

    def test_finalize_daily_notes__errors_when_file_missing(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        mocker.patch.object(
            cmd,
            "_get_daily_notes_file_path",
            return_value=join(temp_week_folder, "missing.md"),
        )
        mocker.patch("taskjournal.commands.commands.exists", return_value=False)
        err = mocker.patch("taskjournal.commands.commands.logger.error")

        # when
        cmd.finalize_daily_notes(fixed_datetime)

        # then
        err.assert_called_once()

    def test_finalize_daily_notes__writes_end_and_spent_time_with_custom_date(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        path = join(temp_week_folder, "2025-01-15-DailyNotes.md")
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value=path)
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
        cmd.file_service.check_finalized_in_file.return_value = False
        content = ["## 2025-01-15 09:30\n", "Other line\n"]
        cmd.file_service.get_lines.return_value = list(content)
        cmd.time_service.get_start_time.return_value = (0, fixed_datetime)
        cmd.time_service.get_total_time_spent.return_value = (2, 15)
        wrap = mocker.patch(
            "taskjournal.services.utils.FormatUtils.wrap_with_format",
            side_effect=lambda s: f"**{s}**",
        )
        info = mocker.patch("taskjournal.commands.commands.logger.info")
        mocker.patch.object(cmd, "_cancel_macos_alarm")
        custom_end = fixed_datetime + timedelta(hours=2, minutes=15)

        # when
        cmd.finalize_daily_notes(custom_end)

        # then
        cmd.file_service.write_lines_to_file.assert_called_once()
        assert wrap.call_count >= 2
        assert any(
            "Daily notes finalized" in " ".join(map(str, c.args))
            for c in info.mock_calls
        )

    def test_finalize_daily_notes__uses_now_when_no_custom_date(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        path = join(temp_week_folder, "2025-01-15-DailyNotes.md")
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value=path)
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
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
            "taskjournal.commands.commands.datetime",
            **{
                "now.return_value": fixed_datetime + timedelta(hours=1),
                "strftime": datetime.strftime,
            },
        )
        mocker.patch.object(cmd, "_cancel_macos_alarm")

        # when
        cmd.finalize_daily_notes(custom_date=None)  # type: ignore[arg-type]

    def test_daily_time__calculates_when_file_exists(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        # given
        path = "/tmp/week3/2025-01-15-DailyNotes.md"
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value=path)
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
        calc = mocker.patch.object(cmd, "_calculate_time")

        # when
        cmd.daily_time(fixed_datetime)

        # then
        calc.assert_called_once_with(path)

    def test_daily_time__warns_when_missing(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        # given
        mocker.patch.object(
            cmd, "_get_daily_notes_file_path", return_value="/missing.md"
        )
        mocker.patch("taskjournal.commands.commands.exists", return_value=False)
        warn = mocker.patch("taskjournal.commands.commands.logger.warning")

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
        mocker.patch.object(cmd, "_get_week_folder", return_value=temp_week_folder)
        cmd.file_service.load_template.return_value = "start={{start_date}}\nend={{end_date}}\nt={{total_time}}\nworked={{total_worked_days}}\nvacation={{vacation_days}}\noffice={{days_at_office}}\nhome={{days_at_home}}\nfireman={{is_fireman_week}}\n{{summary}}"

        files = ["2025-01-13-DailyNotes.md", "2025-01-14-DailyNotes.md"]
        mocker.patch("taskjournal.commands.commands.listdir", return_value=files)

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
            "taskjournal.services.working_days.WorkingDaysService.get_week_stats",
            return_value=mock_stats,
        )

        mocker.patch(
            "taskjournal.services.fireman.FiremanService.is_fireman_week",
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
            cmd, "create_week_summary", new_callable=AsyncMock
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
        mocker.patch.object(cmd, "_get_week_folder", return_value=temp_week_folder)
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
        mocker.patch.object(cmd, "_get_week_folder", return_value=temp_week_folder)
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
            "taskjournal.services.working_days.WorkingDaysService.get_month_stats",
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
        mocker.patch.object(cmd, "_get_week_folder", return_value=temp_week_folder)
        mocker.patch("taskjournal.commands.commands.exists", return_value=False)
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
        mocker.patch.object(cmd, "_get_week_folder", return_value=temp_week_folder)
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
        # when
        cmd.create_retro(fixed_datetime)

        # then
        cmd.file_service.write_to_file.assert_not_called()

    def test_create_backup__logs_backup_path(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        # given
        cmd.backup_service.create.return_value = "/tmp/backup.zip"
        info = mocker.patch("taskjournal.commands.commands.logger.info")

        # when
        cmd.create_backup()

        # then
        assert any(
            "Backup created at: /tmp/backup.zip" in " ".join(map(str, c.args))
            for c in info.mock_calls
        )

    def test__calculate_time__logs_when_elapsed_available(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        # given
        cmd.time_service.calculate_working_hours.return_value = ("09:00", 3.5, datetime(2025, 1, 15, 12, 30))
        info = mocker.patch("taskjournal.commands.commands.logger.info")

        # when
        cmd._calculate_time("/tmp/day.md")

        # then
        assert info.call_count == 3

    def test__calculate_time__logs_error_when_elapsed_missing(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        # given
        cmd.time_service.calculate_working_hours.return_value = (None, None, None)
        err = mocker.patch("taskjournal.commands.commands.logger.error")

        # when
        cmd._calculate_time("/tmp/day.md")

        # then
        err.assert_called_once()

    def test_show_info__logs_day_and_week(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        # given
        info = mocker.patch("taskjournal.commands.commands.logger.info")

        # when
        cmd.show_info(fixed_datetime)

        # then
        # fixed_datetime is 2025-01-15 (Wednesday)
        # 2025-01-15 is ISO week 3
        assert info.call_count == 2
        calls = [c.args[0] for c in info.mock_calls]
        assert "Today is Wednesday, 2025-01-15" in calls[0]
        assert "We are in week 3" in calls[1]

    # ── list / add / update task in daily ────────────────────────────────────

    def test_list_tasks_in_daily__returns_empty_when_file_missing(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value="/missing.md")
        mocker.patch("taskjournal.commands.commands.exists", return_value=False)

        result = cmd.list_tasks_in_daily(fixed_datetime)

        assert result == []

    def test_list_tasks_in_daily__returns_tasks_from_parser(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
        task = Task(id="1", description="Do it", status=Status.TODO)
        cmd.parser.parse.return_value = {"planned_tasks": [task]}

        result = cmd.list_tasks_in_daily(fixed_datetime)

        assert result == [task]

    def test_add_task_to_daily__raises_when_file_missing(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value="/missing.md")
        mocker.patch("taskjournal.commands.commands.exists", return_value=False)

        with raises(FileNotFoundError):
            cmd.add_task_to_daily(fixed_datetime, "New task")

    def test_add_task_to_daily__raises_when_section_not_found(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
        cmd.file_service.get_lines.return_value = ["Some line\n", "Another\n"]

        with raises(ValueError, match="Planned Tasks section not found"):
            cmd.add_task_to_daily(fixed_datetime, "New task")

    def test_add_task_to_daily__inserts_after_last_task(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
        lines = ["## Planned Tasks\n", " - [ ] Existing task\n", "## Notes\n"]
        cmd.file_service.get_lines.return_value = list(lines)

        cmd.add_task_to_daily(fixed_datetime, "New task")

        written = cmd.file_service.write_lines_to_file.call_args[0][1]
        assert any("New task" in ln for ln in written)

    def test_complete_task_in_daily__returns_true_when_found(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
        cmd.file_service.get_lines.return_value = [" - [ ] Do the thing\n"]

        result = cmd.complete_task_in_daily(fixed_datetime, "Do the thing")

        assert result is True
        written = cmd.file_service.write_lines_to_file.call_args[0][1]
        assert "[x]" in written[0]

    def test_block_task_in_daily__returns_false_when_not_found(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
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

    # ── _note_issues / audit ─────────────────────────────────────────────────

    def test_note_issues__returns_empty_for_complete_note(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        cmd.file_service.get_lines.return_value = ["line\n"]
        cmd.time_service.get_start_time.return_value = (0, fixed_datetime)
        cmd.file_service.check_finalized_in_file.return_value = True
        cmd.parser.parse.return_value = {"time_spent": "2h 15m", "summary": ["Accomplished things"]}

        issues = cmd._note_issues("/day.md")

        assert issues == []

    def test_note_issues__reports_missing_start_time(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        cmd.file_service.get_lines.return_value = []
        cmd.time_service.get_start_time.side_effect = ValueError("no start")
        cmd.file_service.check_finalized_in_file.return_value = True
        cmd.parser.parse.return_value = {"time_spent": "1h", "summary": ["Done"]}

        issues = cmd._note_issues("/day.md")

        assert "missing start time" in issues

    def test_note_issues__reports_missing_end_time_and_summary(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        cmd.file_service.get_lines.return_value = ["line\n"]
        cmd.time_service.get_start_time.return_value = (0, datetime(2025, 1, 15))
        cmd.file_service.check_finalized_in_file.return_value = False
        cmd.parser.parse.return_value = {"time_spent": "", "summary": []}

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
        cmd.parser.parse.return_value = {"time_spent": "", "summary": ["Done"]}

        issues = cmd._note_issues("/day.md")

        assert "missing time spent" in issues

    @mark.asyncio
    async def test_create_daily_notes__warns_on_weekend(
        self, cmd: CommandManager, mocker: MockerFixture, temp_week_folder: str
    ) -> None:
        saturday = datetime(2026, 6, 27)  # weekday() == 5
        path = join(temp_week_folder, "2026-06-27-DailyNotes.md")
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value=path)
        cmd.file_service.load_template.return_value = ""
        mocker.patch("taskjournal.commands.commands.exists", return_value=False)
        mocker.patch.object(cmd, "get_previous_day_issues", return_value=None)
        mocker.patch.object(cmd.jira, "get_active_sprint", return_value=None)
        mocker.patch.object(cmd.jira, "get_current_sprint_tasks_not_done_assigned_to_me", new_callable=AsyncMock, return_value=[])
        mocker.patch.object(cmd.jira, "get_current_sprint_tasks_in_code_review", new_callable=AsyncMock, return_value=[])
        mocker.patch.object(cmd.github, "update_status_if_task_reviewed", new_callable=AsyncMock, return_value=[])
        cmd.task_manager.get_previous_pending_tasks.return_value = []
        cmd.task_manager.get_default_tasks.return_value = []
        warn = mocker.patch("taskjournal.commands.commands.logger.warning")

        await cmd.create_daily_notes(saturday)

        assert any("Saturday" in str(c.args) for c in warn.mock_calls)

    def test_get_previous_day_issues__returns_issues_on_weekend(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        # Sunday — checks Saturday
        sunday = datetime(2026, 6, 28)  # weekday() == 6
        saturday_file = "/notes/2026-06-27-DailyNotes.md"
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value=saturday_file)
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
        mocker.patch.object(cmd, "_note_issues", return_value=["missing end time"])

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
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value="/notes/friday.md")
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
        mocker.patch.object(cmd, "_note_issues", return_value=[])

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

        mocker.patch.object(cmd, "_get_daily_notes_file_path", side_effect=_file_path)
        mocker.patch("taskjournal.commands.commands.exists", side_effect=_exists)
        mocker.patch.object(cmd, "_note_issues", return_value=["missing end time"])

        result = cmd.get_previous_day_issues(friday)

        assert result is not None
        date_str, file_path, issues = result
        assert date_str == "2026-06-23"
        assert file_path == tuesday_file

    def test_get_previous_day_issues__returns_none_when_no_notes_in_14_days(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        today = datetime(2026, 6, 26)
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value="/notes/missing.md")
        mocker.patch("taskjournal.commands.commands.exists", return_value=False)

        result = cmd.get_previous_day_issues(today)

        assert result is None

    def test_audit_daily_notes__returns_empty_when_year_dir_missing(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        mocker.patch("taskjournal.commands.commands.exists", return_value=False)

        result = cmd.audit_daily_notes(2025)

        assert result == []

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

        mocker.patch("taskjournal.commands.commands.BASE_DIR", note_dir)
        mocker.patch("taskjournal.commands.commands.TEMPLATE_FORMAT", "md")

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

        mocker.patch("taskjournal.commands.commands.BASE_DIR", note_dir)
        mocker.patch("taskjournal.commands.commands.TEMPLATE_FORMAT", "md")

        daily_results = cmd.search_notes("match", note_type="daily")
        week_results = cmd.search_notes("match", note_type="week")

        assert all("DailyNotes" in r[0] for r in daily_results)
        assert all("week-summary" in r[0] for r in week_results)

    # ── create_one_on_one ────────────────────────────────────────────────────

    def test_create_one_on_one__creates_parent_directory(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch("taskjournal.commands.commands.BASE_DIR", "/base")
        mocker.patch("taskjournal.commands.commands.exists", return_value=False)
        cmd.time_service.get_1on1_name.return_value = "2025-01-15-1on1.md"
        cmd.file_service.load_template.return_value = "template"
        makedirs_mock = mocker.patch("taskjournal.commands.commands.makedirs")

        cmd.create_one_on_one(fixed_datetime)

        makedirs_mock.assert_called_once()
        cmd.file_service.write_to_file.assert_called_once()

    def test_create_one_on_one__skips_write_when_file_exists(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch("taskjournal.commands.commands.BASE_DIR", "/base")
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
        cmd.time_service.get_1on1_name.return_value = "2025-01-15-1on1.md"

        cmd.create_one_on_one(fixed_datetime)

        cmd.file_service.write_to_file.assert_not_called()

    # ── add_topic_to_one_on_one ───────────────────────────────────────────────

    def test_add_topic_to_one_on_one__inserts_topic(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd, "create_one_on_one")
        mocker.patch("taskjournal.commands.commands.BASE_DIR", "/base")
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
        mocker.patch.object(cmd, "create_one_on_one")
        mocker.patch("taskjournal.commands.commands.BASE_DIR", "/base")
        cmd.time_service.get_1on1_name.return_value = "2025-01-15-1on1.md"
        cmd.file_service.get_lines.return_value = ["# Meeting notes\n", "Some text\n"]

        with raises(ValueError, match="Proposal topics.*not found"):
            cmd.add_topic_to_one_on_one(fixed_datetime, "topic")

    # ── get_streak_stats ──────────────────────────────────────────────────────

    def test_get_streak_stats__empty_when_no_notes(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        mocker.patch("taskjournal.commands.commands.BASE_DIR", "/empty")
        mocker.patch("taskjournal.commands.commands.walk", return_value=[])

        stats = cmd.get_streak_stats(datetime(2025, 1, 15))

        assert stats["current"] == 0
        assert stats["total"] == 0

    def test_get_streak_stats__counts_consecutive_weekdays(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        import os
        mocker.patch("taskjournal.commands.commands.BASE_DIR", "/notes")
        files = [
            "2025-01-13-DailyNotes.md",  # Mon
            "2025-01-14-DailyNotes.md",  # Tue
            "2025-01-15-DailyNotes.md",  # Wed (today)
        ]
        mocker.patch(
            "taskjournal.commands.commands.walk",
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
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value="/missing.md")
        mocker.patch("taskjournal.commands.commands.exists", return_value=False)

        with raises(FileNotFoundError):
            await cmd.sync_daily_notes(fixed_datetime)

    @mark.asyncio
    async def test_sync_daily_notes__skips_write_when_all_tasks_present(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value="/day.md")
        mocker.patch("taskjournal.commands.commands.exists", return_value=True)
        existing = Task(id="1", description="Fix bug", status=Status.TODO)
        cmd.parser.parse.return_value = {"planned_tasks": [existing]}
        pending = Task(id="1", description="Fix bug", status=Status.TODO)
        cmd.jira.get_current_sprint_tasks_not_done_assigned_to_me = AsyncMock(return_value=[pending])
        cmd.jira.get_current_sprint_tasks_in_code_review = AsyncMock(return_value=[])
        cmd.github.update_status_if_task_reviewed = AsyncMock()

        await cmd.sync_daily_notes(fixed_datetime)

        cmd.file_service.write_lines_to_file.assert_not_called()

    # ── _schedule_macos_alarm ─────────────────────────────────────────────────

    def test__schedule_macos_alarm__skips_on_non_darwin(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.commands.platform", "linux")
        run = mocker.patch("taskjournal.commands.commands.subprocess_run")

        cmd._schedule_macos_alarm(fixed_datetime, str(tmp_path / ".alarm_job"))

        run.assert_not_called()

    def test__schedule_macos_alarm__logs_info_and_saves_job_on_success(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.commands.platform", "darwin")
        fake_result = mocker.MagicMock()
        fake_result.returncode = 0
        fake_result.stderr = b"job 42 at Tue Jun 30 12:57:00 2026"
        mocker.patch("taskjournal.commands.commands.subprocess_run", return_value=fake_result)
        info = mocker.patch("taskjournal.commands.commands.logger.info")
        alarm_file = str(tmp_path / ".alarm_job")

        cmd._schedule_macos_alarm(fixed_datetime, alarm_file)

        assert any("Alarm set for" in str(c.args) for c in info.mock_calls)
        assert Path(alarm_file).read_text() == "42"

    def test__schedule_macos_alarm__logs_debug_on_failure(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.commands.platform", "darwin")
        fake_result = mocker.MagicMock()
        fake_result.returncode = 1
        fake_result.stderr = b"atd not running"
        mocker.patch("taskjournal.commands.commands.subprocess_run", return_value=fake_result)
        debug = mocker.patch("taskjournal.commands.commands.logger.debug")

        cmd._schedule_macos_alarm(fixed_datetime, str(tmp_path / ".alarm_job"))

        assert any("Could not schedule alarm" in str(c.args) for c in debug.mock_calls)

    def test__schedule_macos_alarm__logs_debug_on_exception(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.commands.platform", "darwin")
        mocker.patch(
            "taskjournal.commands.commands.subprocess_run",
            side_effect=FileNotFoundError("at not found"),
        )
        debug = mocker.patch("taskjournal.commands.commands.logger.debug")

        cmd._schedule_macos_alarm(fixed_datetime, str(tmp_path / ".alarm_job"))

        assert any("Could not schedule alarm" in str(c.args) for c in debug.mock_calls)

    # ── _cancel_macos_alarm ───────────────────────────────────────────────────

    def test__cancel_macos_alarm__skips_on_non_darwin(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.commands.platform", "linux")
        run = mocker.patch("taskjournal.commands.commands.subprocess_run")
        alarm_file = tmp_path / ".alarm_job"
        alarm_file.write_text("42")

        cmd._cancel_macos_alarm(str(alarm_file))

        run.assert_not_called()

    def test__cancel_macos_alarm__skips_when_no_alarm_file(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.commands.platform", "darwin")
        run = mocker.patch("taskjournal.commands.commands.subprocess_run")

        cmd._cancel_macos_alarm(str(tmp_path / ".alarm_job"))

        run.assert_not_called()

    def test__cancel_macos_alarm__cancels_job_and_removes_file(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.commands.platform", "darwin")
        fake_result = mocker.MagicMock()
        fake_result.returncode = 0
        run = mocker.patch("taskjournal.commands.commands.subprocess_run", return_value=fake_result)
        info = mocker.patch("taskjournal.commands.commands.logger.info")
        alarm_file = tmp_path / ".alarm_job"
        alarm_file.write_text("42")

        cmd._cancel_macos_alarm(str(alarm_file))

        run.assert_called_once_with(["atrm", "42"], capture_output=True)
        assert not alarm_file.exists()
        assert any("Alarm cancelled" in str(c.args) for c in info.mock_calls)

    def test__cancel_macos_alarm__logs_debug_when_atrm_fails(
        self, cmd: CommandManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch("taskjournal.commands.commands.platform", "darwin")
        fake_result = mocker.MagicMock()
        fake_result.returncode = 1
        fake_result.stderr = b"no such job"
        mocker.patch("taskjournal.commands.commands.subprocess_run", return_value=fake_result)
        debug = mocker.patch("taskjournal.commands.commands.logger.debug")
        alarm_file = tmp_path / ".alarm_job"
        alarm_file.write_text("99")

        cmd._cancel_macos_alarm(str(alarm_file))

        assert any("Could not cancel alarm" in str(c.args) for c in debug.mock_calls)
