from datetime import datetime, timedelta
from os.path import join
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pytest import mark
from pytest_mock import MockerFixture

from taskjournal.commands.commands import CommandManager


class TestCommands:

    def test__get_week_folder__creates_dir_and_returns_path(
        self,
        cmd: CommandManager,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        get_week_folder = mocker.patch(
            "taskjournal.commands.commands.get_week_folder",
            return_value=temp_week_folder,
        )
        makedirs = mocker.patch("taskjournal.commands.commands.os.makedirs")

        # when
        result = cmd._get_week_folder(fixed_datetime)

        # then
        assert result == temp_week_folder
        get_week_folder.assert_called_once()
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
        get_daily_notes_name = mocker.patch(
            "taskjournal.commands.commands.get_daily_notes_name",
            return_value="2025-01-15-DailyNotes.md",
        )

        # when
        path = cmd._get_daily_notes_file_path(fixed_datetime)

        # then
        assert path.endswith(join("week3", "2025-01-15-DailyNotes.md"))
        get_daily_notes_name.assert_called_once_with(fixed_datetime)

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
        mocker.patch(
            "taskjournal.commands.commands.load_template",
            return_value="date={{date}}, time={{time}}, sprint={{sprint_name}}",
        )
        mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=True)
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
        mocker.patch(
            "taskjournal.commands.commands.load_template",
            return_value="date={{date}}, time={{time}}, sprint={{sprint_name}}\n{{tasks}}\n{{code_review_tasks}}",
        )
        mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=True)
        mocker.patch(
            "taskjournal.commands.commands.get_default_tasks",
            return_value=["task-default"],
        )
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
        mocker.patch(
            "taskjournal.commands.commands.get_previous_pending_tasks",
            return_value=["task-prev"],
        )
        mocker.patch(
            "taskjournal.commands.commands.unique_tasks",
            return_value=["task-default", "task-prev", "task-jira-pending"],
        )
        write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")
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
        info = mocker.patch("taskjournal.commands.commands.logger.info")

        # when
        await cmd.create_daily_notes(fixed_datetime, force=True)

        # then
        write_to_file.assert_called_once()
        assert cmd.task_formatter.format_tasks.call_count == 2
        assert any(
            "Estimated time to finish" in " ".join(map(str, c.args))
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
        mocker.patch(
            "taskjournal.commands.commands.load_template",
            return_value="sprint={{sprint_name}}\n{{tasks}}\n{{code_review_tasks}}",
        )
        mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=False)
        mocker.patch.object(cmd.jira, "get_active_sprint", return_value=None)
        mocker.patch("taskjournal.commands.commands.get_default_tasks", return_value=[])
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
        mocker.patch(
            "taskjournal.commands.commands.get_previous_pending_tasks", return_value=[]
        )
        mocker.patch("taskjournal.commands.commands.unique_tasks", return_value=[])
        write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")

        # when
        await cmd.create_daily_notes(fixed_datetime)

        args, _ = write_to_file.call_args
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
        mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=False)
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
        mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=True)
        mocker.patch(
            "taskjournal.commands.commands.check_finalized_in_file", return_value=False
        )
        content = ["## 2025-01-15 09:30\n", "Other line\n"]
        mocker.patch(
            "taskjournal.commands.commands.get_lines", return_value=list(content)
        )
        mocker.patch(
            "taskjournal.commands.commands.get_start_time",
            return_value=(0, fixed_datetime),
        )
        wrap = mocker.patch(
            "taskjournal.commands.commands.wrap_with_format",
            side_effect=lambda s: f"**{s}**",
        )
        write_lines = mocker.patch("taskjournal.commands.commands.write_lines_to_file")
        info = mocker.patch("taskjournal.commands.commands.logger.info")
        custom_end = fixed_datetime + timedelta(hours=2, minutes=15)

        # when
        cmd.finalize_daily_notes(custom_end)

        # then
        write_lines.assert_called_once()
        assert wrap.call_count >= 2
        assert any(
            "Total Time Spent: 02:15" in " ".join(map(str, c.args))
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
        mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=True)
        mocker.patch(
            "taskjournal.commands.commands.check_finalized_in_file", return_value=False
        )
        mocker.patch(
            "taskjournal.commands.commands.get_lines", return_value=["start\n"]
        )
        mocker.patch(
            "taskjournal.commands.commands.get_start_time",
            return_value=(0, fixed_datetime),
        )
        mocker.patch(
            "taskjournal.commands.commands.wrap_with_format",
            side_effect=lambda s: f"[{s}]",
        )
        mocker.patch("taskjournal.commands.commands.write_lines_to_file")
        # Assumption: patch datetime.now via module-level reference
        mocker.patch(
            "taskjournal.commands.commands.datetime",
            **{
                "now.return_value": fixed_datetime + timedelta(hours=1),
                "strftime": datetime.strftime,
            },
        )

        # when
        cmd.finalize_daily_notes(custom_date=None)  # type: ignore[arg-type]

    def test_daily_time__calculates_when_file_exists(
        self, cmd: CommandManager, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        # given
        path = "/tmp/week3/2025-01-15-DailyNotes.md"
        mocker.patch.object(cmd, "_get_daily_notes_file_path", return_value=path)
        mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=True)
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
        mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=False)
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
        mocker.patch(
            "taskjournal.commands.commands.load_template",
            return_value="start={{start_date}}\nend={{end_date}}\nt={{total_time}}\nworked={{total_worked_days}}\nvacation={{vacation_days}}\noffice={{days_at_office}}\nhome={{days_at_home}}\nfireman={{is_fireman_week}}\n{{summary}}",
        )

        # Mock os.path.exists to return True for Mon/Tue, False otherwise
        # start_of_week (Mon) is 2025-01-13
        # Tue is 2025-01-14
        def mock_exists(path):
            return "2025-01-13" in path or "2025-01-14" in path

        mocker.patch(
            "taskjournal.commands.commands.os.path.exists", side_effect=mock_exists
        )

        mocker.patch(
            "taskjournal.commands.commands.get_daily_notes_name",
            side_effect=lambda d: f"{d.strftime('%Y-%m-%d')}-DailyNotes.md",
        )

        files = ["2025-01-13-DailyNotes.md", "2025-01-14-DailyNotes.md"]
        mocker.patch("taskjournal.commands.commands.os.listdir", return_value=files)

        mocker.patch(
            "taskjournal.commands.commands.get_summary_from_daily_notes",
            side_effect=["Summary 1", "Summary 2"],
        )

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

        mocker.patch.object(cmd.openai, "summarize", side_effect=fake_summarize)

        write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")

        await cmd.create_week_summary(fixed_datetime)

        # then
        args, _ = write_to_file.call_args
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
        mocker.patch(
            "taskjournal.commands.commands.load_template",
            return_value="tasks={{total_tasks}}, epics={{total_epics}}, gh={{github_contributions}}\n{{tasks}}\n{{epics}}",
        )
        # when
        tasks = ["T-1", "T-2", "T-3"]
        mocker.patch.object(
            cmd.jira,
            "get_current_tasks_assigned_to_me_last_6_months",
            new_callable=AsyncMock,
            return_value=tasks,
        )

        mocker.patch(
            "taskjournal.commands.commands.get_unique_epics",
            return_value=["E-1", "E-2"],
        )
        mocker.patch.object(
            cmd.github,
            "get_contributions_last_6_months",
            new_callable=AsyncMock,
            return_value=123,
        )
        mocker.patch.object(
            cmd.github,
            "close",
            new_callable=AsyncMock,
        )
        write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")

        await cmd.create_half_year_review(fixed_datetime)

        content: str = write_to_file.call_args[0][1]
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
        mocker.patch(
            "taskjournal.commands.commands.load_template",
            return_value="tasks={{total_tasks}}, epics={{total_epics}}, gh={{github_contributions}}, summary={{summary}}, time={{total_time}}",
        )
        mocker.patch.object(
            cmd.jira,
            "get_current_tasks_assigned_to_me_last_month",
            new_callable=AsyncMock,
            return_value=["M-1"],
        )
        mocker.patch(
            "taskjournal.commands.commands.get_unique_epics", return_value=["ME-1"]
        )
        mocker.patch.object(
            cmd.github,
            "get_contributions_last_month",
            new_callable=AsyncMock,
            return_value=7,
        )
        mocker.patch.object(
            cmd.github,
            "close",
            new_callable=AsyncMock,
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
            cmd.openai,
            "summarize",
            new_callable=AsyncMock,
            return_value="AI Month Summary",
        )

        write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")

        # when
        await cmd.create_month_review(fixed_datetime)

        content: str = write_to_file.call_args[0][1]
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
        mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=False)
        mocker.patch(
            "taskjournal.commands.commands.load_template",
            return_value="retro {{sprint_name}}",
        )
        # Use SimpleNamespace here too to avoid MagicMock 'name' kwarg conflict
        mocker.patch.object(
            cmd.jira, "get_active_sprint", return_value=SimpleNamespace(name="Alpha")
        )
        write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")

        cmd.create_retro(fixed_datetime)

        # when
        content: str = write_to_file.call_args[0][1]
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
        mocker.patch("taskjournal.commands.commands.os.path.exists", return_value=True)
        write_to_file = mocker.patch("taskjournal.commands.commands.write_to_file")

        # when
        cmd.create_retro(fixed_datetime)

        # then
        write_to_file.assert_not_called()

    def test_create_backup__logs_backup_path(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch(
            "taskjournal.commands.commands.create_backup",
            return_value="/tmp/backup.zip",
        )
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
        mocker.patch(
            "taskjournal.commands.commands.calculate_working_hours",
            return_value=("09:00", 3.5, datetime(2025, 1, 15, 12, 30)),
        )
        info = mocker.patch("taskjournal.commands.commands.logger.info")

        # when
        cmd._calculate_time("/tmp/day.md")

        # then
        assert info.call_count == 3

    def test__calculate_time__logs_error_when_elapsed_missing(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch(
            "taskjournal.commands.commands.calculate_working_hours",
            return_value=(None, None, None),
        )
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
