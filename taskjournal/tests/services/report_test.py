from datetime import datetime
from unittest.mock import AsyncMock

from pytest import mark
from pytest_mock import MockerFixture

from taskjournal.services.report import ReportService


class TestReportService:

    @mark.asyncio
    async def test_create_week_report__writes_to_file(
        self,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        service = ReportService(
            jira_service=mocker.MagicMock(),
            github_service=mocker.MagicMock(),
            openai_service=mocker.MagicMock(),
            task_formatter=mocker.MagicMock(),
        )
        mocker.patch(
            "taskjournal.services.report.get_week_folder", return_value=temp_week_folder
        )
        mocker.patch(
            "taskjournal.services.report.load_template",
            return_value="Week: {{week_number}}, Time: {{total_time}}",
        )
        mocker.patch("taskjournal.services.report.os.path.exists", return_value=True)
        mocker.patch(
            "taskjournal.services.report.get_tasks_from_daily_notes", return_value=[]
        )
        mocker.patch(
            "taskjournal.services.report.get_total_time_from_daily_notes",
            return_value=3600,
        )
        mocker.patch(
            "taskjournal.services.report.get_summary_from_daily_notes",
            return_value="Summary",
        )
        mocker.patch("taskjournal.services.report.unique_tasks", return_value=[])
        mocker.patch("taskjournal.services.report.get_unique_epics", return_value=[])

        write_to_file = mocker.patch("taskjournal.services.report.write_to_file")

        # when
        await service.create_week_report(fixed_datetime)

        # then
        write_to_file.assert_called_once()
        args, _ = write_to_file.call_args
        assert "Time: 05:00" in args[1]  # 3600 * 5 days = 5 hours

    @mark.asyncio
    async def test_create_month_review__calls_jira_and_writes_file(
        self,
        mocker: MockerFixture,
        fixed_datetime: datetime,
    ) -> None:
        # given
        service = ReportService(
            jira_service=mocker.MagicMock(),
            task_formatter=mocker.MagicMock(),
        )
        service.jira.get_current_tasks_assigned_to_me_last_month = AsyncMock(
            return_value=["task1"]
        )
        mocker.patch(
            "taskjournal.services.report.load_template", return_value="Month: {{month}}"
        )
        mocker.patch("taskjournal.services.report.os.makedirs")
        write_to_file = mocker.patch("taskjournal.services.report.write_to_file")

        # when
        await service.create_month_review(fixed_datetime)

        # then
        service.jira.get_current_tasks_assigned_to_me_last_month.assert_called_once()
        write_to_file.assert_called_once()

    @mark.asyncio
    async def test_create_half_year_review__calls_jira_and_writes_file(
        self,
        mocker: MockerFixture,
        fixed_datetime: datetime,
    ) -> None:
        # given
        service = ReportService(
            jira_service=mocker.MagicMock(),
            task_formatter=mocker.MagicMock(),
        )
        service.jira.get_current_tasks_assigned_to_me_last_6_months = AsyncMock(
            return_value=["task1"]
        )
        mocker.patch(
            "taskjournal.services.report.load_template",
            return_value="Period: {{period}}",
        )
        mocker.patch("taskjournal.services.report.os.makedirs")
        write_to_file = mocker.patch("taskjournal.services.report.write_to_file")

        # when
        await service.create_half_year_review(fixed_datetime)

        # then
        service.jira.get_current_tasks_assigned_to_me_last_6_months.assert_called_once()
        write_to_file.assert_called_once()

    def test_create_retro__writes_file(
        self,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        service = ReportService()
        mocker.patch(
            "taskjournal.services.report.get_week_folder", return_value=temp_week_folder
        )
        mocker.patch(
            "taskjournal.services.report.load_template", return_value="Retro: {{date}}"
        )
        write_to_file = mocker.patch("taskjournal.services.report.write_to_file")

        # when
        service.create_retro(fixed_datetime)

        # then
        write_to_file.assert_called_once()

    def test_create_1on1__writes_file(
        self,
        mocker: MockerFixture,
        fixed_datetime: datetime,
        temp_week_folder: str,
    ) -> None:
        # given
        service = ReportService()
        mocker.patch(
            "taskjournal.services.report.get_week_folder", return_value=temp_week_folder
        )
        mocker.patch(
            "taskjournal.services.report.get_1on1_name", return_value="1on1.md"
        )
        mocker.patch(
            "taskjournal.services.report.load_template", return_value="1on1: {{date}}"
        )
        write_to_file = mocker.patch("taskjournal.services.report.write_to_file")

        # when
        service.create_1on1(fixed_datetime)

        # then
        write_to_file.assert_called_once()
