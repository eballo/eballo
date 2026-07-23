from collections.abc import Callable
from datetime import datetime
from unittest.mock import MagicMock

from freezegun import freeze_time

from taskjournal.models.parsed_note import ParsedNote
from pytest import LogCaptureFixture
from pytest_mock import MockerFixture
from typer.testing import Result

from taskjournal.models.task import Status, Task


class TestAuditAutoFix:

    @freeze_time("2026-01-19 10:00:00")
    def test_fix_calls_fix_note_automatically_for_each_incomplete_file(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.audit_daily_notes.return_value = [
            ("2026-01-05", "/day.md", ["missing summary"]),
        ]
        cli_manager.count_week_folders.return_value = 1
        cli_manager.audit_weekly_coverage.return_value = []
        cli_manager.fix_note_automatically = mocker.AsyncMock(return_value=["summary"])

        result = invoke_cli(["daily", "audit", "--fix"])

        assert result.exit_code == 0
        cli_manager.fix_note_automatically.assert_called_once_with(
            "2026-01-05", "/day.md", ["missing summary"]
        )
        assert "Fixed: summary" in result.stdout

    @freeze_time("2026-01-19 10:00:00")
    def test_fix_reports_when_nothing_could_be_fixed(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.audit_daily_notes.return_value = [
            ("2026-01-05", "/day.md", ["missing start time"]),
        ]
        cli_manager.count_week_folders.return_value = 1
        cli_manager.audit_weekly_coverage.return_value = []
        cli_manager.fix_note_automatically = mocker.AsyncMock(return_value=[])

        result = invoke_cli(["daily", "audit", "--fix"])

        assert result.exit_code == 0
        assert "Nothing could be fixed automatically" in result.stdout

    @freeze_time("2026-01-19 10:00:00")
    def test_fix_not_called_without_fix_flag(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.audit_daily_notes.return_value = [
            ("2026-01-05", "/day.md", ["missing summary"]),
        ]
        cli_manager.count_week_folders.return_value = 1
        cli_manager.audit_weekly_coverage.return_value = []
        cli_manager.fix_note_automatically = mocker.AsyncMock(return_value=["summary"])

        result = invoke_cli(["daily", "audit"])

        assert result.exit_code == 0
        cli_manager.fix_note_automatically.assert_not_called()


class TestDailyStatus:

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_status_shows_open_file(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_week_folder_and_daily_notes_file",
                     return_value=("/day.md", "/week"))
        mocker.patch("taskjournal.cli.commands.daily.exists", return_value=True)
        mocker.patch("taskjournal.cli.commands.daily.TimeService.calculate_working_hours",
                     return_value=(datetime(2026, 1, 19, 9, 0), 1.5, datetime(2026, 1, 19, 18, 0)))
        mocker.patch("taskjournal.cli.commands.daily.TimeService.seconds_to_hours_minutes",
                     return_value=(1, 30))
        mocker.patch("taskjournal.cli.commands.daily.FileService.check_finalized_in_file",
                     return_value=False)
        task = Task(id="1", description="Fix", status=Status.TODO)
        cli_manager.parser.parse.return_value = ParsedNote(planned_tasks=[task])

        result = invoke_cli(["daily", "status"])

        assert result.exit_code == 0
        assert "Open" in result.output or "not finalized" in result.output

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_status_exits_when_file_missing(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
    ) -> None:
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_week_folder_and_daily_notes_file",
                     return_value=("/missing.md", "/week"))
        mocker.patch("taskjournal.cli.commands.daily.exists", return_value=False)

        result = invoke_cli(["daily", "status"])

        assert result.exit_code == 1
        assert "No daily notes found" in caplog.text


class TestDailyCheck:

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_check_all_pass(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
    ) -> None:
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_week_folder_and_daily_notes_file",
                     return_value=("/day.md", "/week"))
        mocker.patch("taskjournal.cli.commands.daily.exists", return_value=True)
        mocker.patch("taskjournal.cli.commands.daily.FileService.get_lines",
                     return_value=["line\n"])
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_start_time",
                     return_value=(0, datetime(2026, 1, 19, 9, 0)))
        mocker.patch("taskjournal.cli.commands.daily.FileService.check_finalized_in_file",
                     return_value=True)
        task = Task(id="1", description="Done", status=Status.DONE)
        cli_manager.parser.parse.return_value = ParsedNote(planned_tasks=[task], summary=["Summary"])

        result = invoke_cli(["daily", "check"])

        assert result.exit_code == 0

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_check_exits_when_file_missing(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
    ) -> None:
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_week_folder_and_daily_notes_file",
                     return_value=("/missing.md", "/week"))
        mocker.patch("taskjournal.cli.commands.daily.exists", return_value=False)

        result = invoke_cli(["daily", "check"])

        assert result.exit_code == 1
        assert "No daily notes found" in caplog.text


class TestDailySync:

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_sync_calls_manager(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
    ) -> None:
        from unittest.mock import AsyncMock
        cli_manager.sync_daily_notes = AsyncMock()

        result = invoke_cli(["daily", "sync"])

        assert result.exit_code == 0
        cli_manager.sync_daily_notes.assert_awaited_once_with(datetime(2026, 1, 19, 10, 0, 0))

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_sync_logs_error_on_file_not_found(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
    ) -> None:
        from unittest.mock import AsyncMock
        cli_manager.sync_daily_notes = AsyncMock(side_effect=FileNotFoundError("no file"))

        result = invoke_cli(["daily", "sync"])

        assert result.exit_code == 1
        assert "no file" in caplog.text

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_sync_without_prs_flag_does_not_sync_prs(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        from unittest.mock import AsyncMock
        cli_manager.sync_daily_notes = AsyncMock()
        cli_manager.sync_prs = AsyncMock()

        result = invoke_cli(["daily", "sync"])

        assert result.exit_code == 0
        cli_manager.sync_prs.assert_not_called()

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_sync_with_prs_flag_also_syncs_prs(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        from unittest.mock import AsyncMock
        cli_manager.sync_daily_notes = AsyncMock()
        cli_manager.sync_prs = AsyncMock(return_value=2)

        result = invoke_cli(["daily", "sync", "--prs"])

        assert result.exit_code == 0
        cli_manager.sync_prs.assert_awaited_once_with(datetime(2026, 1, 19, 10, 0, 0))
        assert "Added 2 PR(s)" in result.stdout

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_sync_with_prs_flag_reports_when_none_added(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        from unittest.mock import AsyncMock
        cli_manager.sync_daily_notes = AsyncMock()
        cli_manager.sync_prs = AsyncMock(return_value=0)

        result = invoke_cli(["daily", "sync", "--prs"])

        assert result.exit_code == 0
        assert "All PRs already in daily notes" in result.stdout


class TestDailyTask:

    @freeze_time("2026-01-19 10:00:00")
    def test_task_list_shows_tasks(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        task = Task(id="1", description="Fix bug", status=Status.TODO)
        cli_manager.list_tasks_in_daily.return_value = [task]

        result = invoke_cli(["task", "list"])

        assert result.exit_code == 0
        assert "Fix bug" in result.output

    @freeze_time("2026-01-19 10:00:00")
    def test_task_list_logs_when_empty(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.list_tasks_in_daily.return_value = []

        result = invoke_cli(["task", "list"])

        assert result.exit_code == 0

    @freeze_time("2026-01-19 10:00:00")
    def test_task_add_calls_manager(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        result = invoke_cli(["task", "add", "New task"])

        assert result.exit_code == 0
        cli_manager.add_task_to_daily.assert_called_once_with(
            datetime(2026, 1, 19, 10, 0, 0), "New task"
        )

    @freeze_time("2026-01-19 10:00:00")
    def test_task_add_logs_error_on_failure(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.add_task_to_daily.side_effect = ValueError("no section")

        result = invoke_cli(["task", "add", "something"])

        assert result.exit_code == 1
        assert "no section" in caplog.text

    @freeze_time("2026-01-19 10:00:00")
    def test_task_done_marks_task(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.complete_task_in_daily.return_value = True

        result = invoke_cli(["task", "done", "Fix bug"])

        assert result.exit_code == 0
        cli_manager.complete_task_in_daily.assert_called_once()

    @freeze_time("2026-01-19 10:00:00")
    def test_task_done_warns_when_not_found(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.complete_task_in_daily.return_value = False

        result = invoke_cli(["task", "done", "nonexistent"])

        assert result.exit_code == 0
        assert "No matching task found" in caplog.text

    @freeze_time("2026-01-19 10:00:00")
    def test_task_block_marks_task(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.block_task_in_daily.return_value = True

        result = invoke_cli(["task", "block", "Blocked item"])

        assert result.exit_code == 0
        cli_manager.block_task_in_daily.assert_called_once()

    @freeze_time("2026-01-19 10:00:00")
    def test_task_block_warns_when_not_found(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.block_task_in_daily.return_value = False

        result = invoke_cli(["task", "block", "nonexistent"])

        assert result.exit_code == 0
        assert "No matching task found" in caplog.text

    @freeze_time("2026-01-19 10:00:00")
    def test_task_block_logs_error_on_file_not_found(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.block_task_in_daily.side_effect = FileNotFoundError("no file")

        result = invoke_cli(["task", "block", "something"])

        assert result.exit_code == 1
        assert "no file" in caplog.text

    @freeze_time("2026-01-19 10:00:00")
    def test_task_done_logs_error_on_file_not_found(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.complete_task_in_daily.side_effect = FileNotFoundError("no file")

        result = invoke_cli(["task", "done", "something"])

        assert result.exit_code == 1
        assert "no file" in caplog.text

    @freeze_time("2026-01-19 10:00:00")
    def test_task_wip_marks_task(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.wip_task_in_daily.return_value = True

        result = invoke_cli(["task", "wip", "Current task"])

        assert result.exit_code == 0
        cli_manager.wip_task_in_daily.assert_called_once()

    @freeze_time("2026-01-19 10:00:00")
    def test_task_wip_warns_when_not_found(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.wip_task_in_daily.return_value = False

        result = invoke_cli(["task", "wip", "nonexistent"])

        assert result.exit_code == 0
        assert "No matching task found" in caplog.text

    @freeze_time("2026-01-19 10:00:00")
    def test_task_wip_logs_error_on_file_not_found(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.wip_task_in_daily.side_effect = FileNotFoundError("no file")

        result = invoke_cli(["task", "wip", "something"])

        assert result.exit_code == 1
        assert "no file" in caplog.text


class TestDailyAudit:

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_audit_no_notes_logs_warning(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.audit_daily_notes.return_value = []

        result = invoke_cli(["daily", "audit"])

        assert result.exit_code == 0
        assert "No daily notes found" in caplog.text

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_audit_shows_issues(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        cli_manager.audit_daily_notes.return_value = [
            ("2026-01-05", "/day.md", ["missing end time"]),
            ("2026-01-06", "/day2.md", []),
        ]
        cli_manager.count_week_folders.return_value = 3
        cli_manager.audit_weekly_coverage.return_value = []

        result = invoke_cli(["daily", "audit"])

        assert result.exit_code == 0
        cli_manager.audit_daily_notes.assert_called_once()

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_audit_with_coverage_gaps(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.audit_daily_notes.return_value = [
            ("2026-01-06", "/day.md", []),
        ]
        cli_manager.count_week_folders.return_value = 2
        cli_manager.audit_weekly_coverage.return_value = [
            ("week02", ["2026-01-07", "2026-01-08"]),
        ]

        result = invoke_cli(["daily", "audit"])

        assert result.exit_code == 0
        assert "2026-01-07" in result.output or "week02" in result.output

    def test_daily_audit_past_year_no_current_week(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.audit_daily_notes.return_value = [
            ("2024-06-01", "/day.md", []),
        ]
        cli_manager.count_week_folders.return_value = 52
        cli_manager.audit_weekly_coverage.return_value = []

        result = invoke_cli(["daily", "audit", "--year", "2024"])

        assert result.exit_code == 0


class TestDailyCheck:

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_check_with_no_tasks(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_week_folder_and_daily_notes_file",
                     return_value=("/day.md", "/week"))
        mocker.patch("taskjournal.cli.commands.daily.exists", return_value=True)
        mocker.patch("taskjournal.cli.commands.daily.FileService.get_lines", return_value=["line\n"])
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_start_time",
                     return_value=(0, datetime(2026, 1, 19, 9, 0)))
        mocker.patch("taskjournal.cli.commands.daily.FileService.check_finalized_in_file",
                     return_value=True)
        cli_manager.parser.parse.return_value = ParsedNote(
            planned_tasks=[],
            summary=["Some summary"],
        )

        result = invoke_cli(["daily", "check"])

        assert result.exit_code == 0
        assert "No tasks found" in result.output

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_check_all_pass_shows_success(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_week_folder_and_daily_notes_file",
                     return_value=("/day.md", "/week"))
        mocker.patch("taskjournal.cli.commands.daily.exists", return_value=True)
        mocker.patch("taskjournal.cli.commands.daily.FileService.get_lines", return_value=["line\n"])
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_start_time",
                     return_value=(0, datetime(2026, 1, 19, 9, 0)))
        mocker.patch("taskjournal.cli.commands.daily.FileService.check_finalized_in_file",
                     return_value=True)
        task = Task(id="1", description="Done task", status=Status.DONE)
        cli_manager.parser.parse.return_value = ParsedNote(
            planned_tasks=[task],
            summary=["Great day!"],
        )

        result = invoke_cli(["daily", "check"])

        assert result.exit_code == 0
        assert "All checks passed" in result.output

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_check_multiple_issues_shows_plural(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
    ) -> None:
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_week_folder_and_daily_notes_file",
                     return_value=("/day.md", "/week"))
        mocker.patch("taskjournal.cli.commands.daily.exists", return_value=True)
        mocker.patch("taskjournal.cli.commands.daily.FileService.get_lines",
                     side_effect=ValueError("no start time"))
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_start_time",
                     side_effect=ValueError("no start time"))
        mocker.patch("taskjournal.cli.commands.daily.FileService.check_finalized_in_file",
                     return_value=False)
        cli_manager.parser.parse.return_value = ParsedNote(
            planned_tasks=[],
            summary=[],
        )

        result = invoke_cli(["daily", "check"])

        assert result.exit_code == 0
        assert "issues" in caplog.text


class TestDailyStatus:

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_status_shows_all_timing_details(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_week_folder_and_daily_notes_file",
                     return_value=("/day.md", "/week"))
        mocker.patch("taskjournal.cli.commands.daily.exists", return_value=True)
        mocker.patch("taskjournal.cli.commands.daily.TimeService.calculate_working_hours",
                     return_value=(datetime(2026, 1, 19, 9, 0), 2.5, datetime(2026, 1, 19, 18, 0)))
        mocker.patch("taskjournal.cli.commands.daily.TimeService.seconds_to_hours_minutes",
                     return_value=(2, 30))
        mocker.patch("taskjournal.cli.commands.daily.FileService.check_finalized_in_file",
                     return_value=False)
        tasks = [
            Task(id="1", description="Done", status=Status.DONE),
            Task(id="2", description="Pending", status=Status.TODO),
            Task(id="3", description="Blocked", status=Status.BLOCKED),
        ]
        cli_manager.parser.parse.return_value = ParsedNote(planned_tasks=tasks)

        result = invoke_cli(["daily", "status"])

        assert result.exit_code == 0
        assert "09:00" in result.output
        assert "18:00" in result.output

    @freeze_time("2026-01-19 10:00:00")
    def test_daily_status_finalized_shows_correct_state(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("taskjournal.cli.commands.daily.TimeService.get_week_folder_and_daily_notes_file",
                     return_value=("/day.md", "/week"))
        mocker.patch("taskjournal.cli.commands.daily.exists", return_value=True)
        mocker.patch("taskjournal.cli.commands.daily.TimeService.calculate_working_hours",
                     return_value=(None, None, None))
        mocker.patch("taskjournal.cli.commands.daily.TimeService.seconds_to_hours_minutes",
                     return_value=(0, 0))
        mocker.patch("taskjournal.cli.commands.daily.FileService.check_finalized_in_file",
                     return_value=True)
        cli_manager.parser.parse.return_value = ParsedNote(planned_tasks=[])

        result = invoke_cli(["daily", "status"])

        assert result.exit_code == 0
        assert "Finalized" in result.output


class TestDailyOpen:

    def test_daily_open_calls_editor(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        mocker.patch("taskjournal.services.time.TimeService.resolve_daily_notes_file", return_value=("/day.md", "/week/"))
        mocker.patch("taskjournal.cli.commands.daily.exists", return_value=True)
        run_proc = mocker.patch("taskjournal.cli.commands.daily.subprocess_run")
        mocker.patch("taskjournal.cli.commands.daily.environ", {"EDITOR": "vim"})

        result = invoke_cli(["daily", "open"])

        assert result.exit_code == 0
        run_proc.assert_called_once_with(["vim", "/day.md"])

    def test_daily_open_exits_when_file_missing(
        self,
        mocker: MockerFixture,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        caplog: LogCaptureFixture,
    ) -> None:
        mocker.patch("taskjournal.services.time.TimeService.resolve_daily_notes_file", return_value=("/day.md", "/week/"))
        mocker.patch("taskjournal.cli.commands.daily.exists", return_value=False)

        result = invoke_cli(["daily", "open"])

        assert result.exit_code == 1
        assert "No daily notes found" in caplog.text
