import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pytest import mark
from pytest_mock import MockerFixture

from taskjournal.services.daily import DailyService


class TestDailyService:

    def test__get_daily_notes_file_path__joins_week_folder_and_filename(
        self,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        mocker.patch(
            "taskjournal.services.daily.get_week_folder", return_value=temp_week_folder
        )
        mocker.patch(
            "taskjournal.services.daily.get_daily_notes_name",
            return_value="2025-01-15-DailyNotes.md",
        )
        service = DailyService()

        # when
        path = service._get_daily_notes_file_path(fixed_datetime)

        # then
        assert path == os.path.join(temp_week_folder, "2025-01-15-DailyNotes.md")

    @mark.asyncio
    async def test_create_daily_notes__skips_when_file_exists_and_not_forced(
        self,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        service = DailyService(
            jira_service=mocker.MagicMock(),
            openai_service=mocker.MagicMock(),
            task_formatter=mocker.MagicMock(),
        )
        path = os.path.join(temp_week_folder, "2025-01-15-DailyNotes.md")
        mocker.patch.object(service, "_get_daily_notes_file_path", return_value=path)
        mocker.patch("taskjournal.services.daily.os.path.exists", return_value=True)
        warn = mocker.patch("taskjournal.services.daily.logger.warning")

        # when
        await service.create_daily_notes(fixed_datetime, force=False)

        # then
        warn.assert_called_once()
        service.task_formatter.format_tasks.assert_not_called()

    @mark.asyncio
    async def test_create_daily_notes__creates_when_forced_even_if_exists(
        self,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        service = DailyService(
            jira_service=mocker.MagicMock(),
            openai_service=mocker.MagicMock(),
            task_formatter=mocker.MagicMock(),
        )
        path = os.path.join(temp_week_folder, "2025-01-15-DailyNotes.md")
        mocker.patch.object(service, "_get_daily_notes_file_path", return_value=path)
        mocker.patch(
            "taskjournal.services.daily.load_template",
            return_value="sprint={{sprint_name}}\n{{tasks}}\n{{jira_tasks}}",
        )
        mocker.patch("taskjournal.services.daily.os.path.exists", return_value=True)
        mocker.patch(
            "taskjournal.services.daily.get_default_tasks",
            return_value=["task-default"],
        )
        mocker.patch(
            "taskjournal.services.daily.get_previous_pending_tasks",
            return_value=["task-prev"],
        )

        service.jira.get_active_sprint.return_value = SimpleNamespace(name="Sprint 42")
        service.jira.get_current_sprint_tasks_not_done_assigned_to_me = AsyncMock(
            return_value=["task-jira"]
        )

        write_to_file = mocker.patch("taskjournal.services.daily.write_to_file")

        # when
        await service.create_daily_notes(fixed_datetime, force=True)

        # then
        write_to_file.assert_called_once()
        assert service.task_formatter.format_tasks.call_count == 2

    def test_finalize_daily_notes__errors_when_file_missing(
        self,
        mocker: MockerFixture,
        fixed_datetime: datetime,
    ) -> None:
        # given
        service = DailyService()
        mocker.patch.object(
            service, "_get_daily_notes_file_path", return_value="/missing.md"
        )
        mocker.patch("taskjournal.services.daily.os.path.exists", return_value=False)
        err = mocker.patch("taskjournal.services.daily.logger.error")

        # when
        service.finalize_daily_notes(fixed_datetime)

        # then
        err.assert_called_once()

    def test_finalize_daily_notes__writes_end_and_spent_time(
        self,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        service = DailyService()
        path = os.path.join(temp_week_folder, "2025-01-15-DailyNotes.md")
        mocker.patch.object(service, "_get_daily_notes_file_path", return_value=path)
        mocker.patch("taskjournal.services.daily.os.path.exists", return_value=True)
        mocker.patch("taskjournal.services.daily.get_lines", return_value=["line1\n"])
        mocker.patch(
            "taskjournal.services.daily.get_start_time",
            return_value=(0, fixed_datetime),
        )
        mocker.patch(
            "taskjournal.services.daily.get_total_time_spent", return_value=(2, 15)
        )
        mocker.patch(
            "taskjournal.services.daily.load_template",
            return_value="End: {{end_time}}, Total: {{total_time}}",
        )
        write_to_file = mocker.patch("taskjournal.services.daily.write_to_file")

        # when
        service.finalize_daily_notes(fixed_datetime + timedelta(hours=2, minutes=15))

        # then
        write_to_file.assert_called_once()
        args, kwargs = write_to_file.call_args
        assert "Total: 02:15" in args[1]
        assert kwargs.get("mode") == "a"

    def test_daily_time__calculates_when_file_exists(
        self, mocker: MockerFixture, fixed_datetime: datetime
    ) -> None:
        # given
        service = DailyService()
        path = "/tmp/day.md"
        mocker.patch.object(service, "_get_daily_notes_file_path", return_value=path)
        mocker.patch("taskjournal.services.daily.os.path.exists", return_value=True)
        calc = mocker.patch(
            "taskjournal.services.daily.calculate_working_hours",
            return_value=(fixed_datetime, 8.0, fixed_datetime),
        )
        info = mocker.patch("taskjournal.services.daily.logger.info")

        # when
        service.daily_time(fixed_datetime)

        # then
        calc.assert_called_once_with(path)
        assert info.call_count == 3
