from datetime import datetime

from pytest import mark
from pytest_mock import MockerFixture

from taskjournal.commands.commands import CommandManager


class TestCommands:
    @mark.asyncio
    async def test_create_daily_notes_delegates_to_daily_service(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        # when
        await cmd.create_daily_notes(
            fixed_datetime, force=True, firefighter=True, work_from="Home"
        )

        # then
        cmd.daily_service.create_daily_notes.assert_called_once_with(
            fixed_datetime, True, True, "Home"
        )

    def test_finalize_daily_notes_delegates_to_daily_service(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        # when
        cmd.finalize_daily_notes(fixed_datetime)

        # then
        cmd.daily_service.finalize_daily_notes.assert_called_once_with(fixed_datetime)

    def test_daily_time_delegates_to_daily_service(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        # when
        cmd.daily_time(fixed_datetime)

        # then
        cmd.daily_service.daily_time.assert_called_once_with(fixed_datetime)

    @mark.asyncio
    async def test_create_week_summary_delegates_to_report_service(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        # when
        await cmd.create_week_summary(fixed_datetime)

        # then
        cmd.report_service.create_week_report.assert_called_once_with(fixed_datetime)

    @mark.asyncio
    async def test_create_half_year_review_delegates_to_report_service(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        # when
        await cmd.create_half_year_review(fixed_datetime)

        # then
        cmd.report_service.create_half_year_review.assert_called_once_with(
            fixed_datetime
        )

    @mark.asyncio
    async def test_create_month_review_delegates_to_report_service(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        # when
        await cmd.create_month_review(fixed_datetime)

        # then
        cmd.report_service.create_month_review.assert_called_once_with(fixed_datetime)

    def test_create_retro_delegates_to_report_service(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        # when
        cmd.create_retro(fixed_datetime)

        # then
        cmd.report_service.create_retro.assert_called_once_with(fixed_datetime)

    def test_create_one_on_one_delegates_to_report_service(
        self, cmd: CommandManager, fixed_datetime: datetime
    ) -> None:
        # when
        cmd.create_one_on_one(fixed_datetime)

        # then
        cmd.report_service.create_1on1.assert_called_once_with(fixed_datetime)

    def test_create_backup_delegates_to_backup_service(
        self, cmd: CommandManager, mocker: MockerFixture
    ) -> None:
        # given
        mock_backup = mocker.patch("taskjournal.commands.commands.create_backup")

        # when
        cmd.create_backup()

        # then
        mock_backup.assert_called_once()
