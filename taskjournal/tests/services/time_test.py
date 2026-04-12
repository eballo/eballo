from datetime import datetime, timedelta

from freezegun import freeze_time
from pytest import raises
from pytest_mock import MockerFixture

from taskjournal.services.time import TimeService


class TestTime:

    @freeze_time("2025-01-19 12:00:00")
    def test_calculate_working_hours_valid(self, mocker: MockerFixture) -> None:
        # given
        created_time = "2025-01-19 09:00:00"
        mock_open = mocker.mock_open(read_data=f"Start time: {created_time}\n")
        mocker.patch("builtins.open", mock_open)
        mocker.patch(
            "taskjournal.services.time.TimeService.get_start_time",
            return_value=(0, datetime.strptime(created_time, "%Y-%m-%d %H:%M:%S")),
        )

        # when
        created, elapsed, finish = TimeService.calculate_working_hours("notes.txt")

        # then
        assert created == datetime.strptime(created_time, "%Y-%m-%d %H:%M:%S")
        assert round(elapsed, 1) == 3.0
        assert finish == created + timedelta(hours=9)

    def test_calculate_working_hours_no_start_line(self, mocker: MockerFixture) -> None:
        # given
        mock_open = mocker.mock_open(read_data="Task: something\nAnother line\n")
        mocker.patch("builtins.open", mock_open)
        mock_logger = mocker.patch("taskjournal.services.time.logger")
        mocker.patch(
            "taskjournal.services.time.TimeService.get_start_time",
            side_effect=ValueError("Start time not found"),
        )

        # when
        created, elapsed, finish = TimeService.calculate_working_hours("notes.txt")

        # then
        assert created is None
        assert elapsed is None
        assert finish is None
        mock_logger.error.assert_called_once()

    def test_calculate_working_hours_malformed_start(
        self, mocker: MockerFixture
    ) -> None:
        # given
        mock_open = mocker.mock_open(read_data="Start time: not-a-date\n")
        mocker.patch("builtins.open", mock_open)
        mock_logger = mocker.patch("taskjournal.services.time.logger")

        # when
        created, elapsed, finish = TimeService.calculate_working_hours("notes.txt")

        # then
        assert created is None
        assert elapsed is None
        assert finish is None
        mock_logger.error.assert_called_once()

    def test_calculate_working_hours_file_error(self, mocker: MockerFixture) -> None:
        # given
        mocker.patch("builtins.open", side_effect=OSError("Read fail"))
        mock_logger = mocker.patch("taskjournal.services.time.logger")

        # when
        created, elapsed, finish = TimeService.calculate_working_hours("notes.txt")

        # then
        assert created is None
        assert elapsed is None
        assert finish is None
        mock_logger.error.assert_called_once()

    def test_get_total_time_from_daily_notes_single_entry(
        self,
        mocker: MockerFixture,
    ) -> None:
        # given
        mocker.patch("taskjournal.services.utils.TEMPLATE_FORMAT", "txt")
        mock_open = mocker.mock_open(read_data=" Time Spent: 01:15\n")
        mocker.patch("builtins.open", mock_open)

        # when
        total_seconds = TimeService.get_total_time_from_daily_notes("file.txt")
        # then
        assert total_seconds == 1 * 3600 + 15 * 60

    def test_get_total_time_from_daily_notes_multiple_entries(
        self,
        mocker: MockerFixture,
    ) -> None:
        # given
        mocker.patch("taskjournal.services.utils.TEMPLATE_FORMAT", "txt")
        data = " Time Spent: 00:30\nTask: something\n Time Spent: 01:00\n"
        mock_open = mocker.mock_open(read_data=data)
        mocker.patch("builtins.open", mock_open)

        # when
        total = TimeService.get_total_time_from_daily_notes("file.txt")
        # then
        assert total == 5400  # 1.5 hours

    def test_get_total_time_from_daily_notes_malformed_ignored(
        self,
        mocker: MockerFixture,
    ) -> None:
        # given
        mocker.patch("taskjournal.services.utils.TEMPLATE_FORMAT", "txt")
        data = " Time Spent: abc\n Time Spent: 01:00"
        mock_open = mocker.mock_open(read_data=data)
        mocker.patch("builtins.open", mock_open)

        # when
        total = TimeService.get_total_time_from_daily_notes("file.txt")
        # then
        assert total == 3600

    def test_estimated_finish_time(self) -> None:
        # given
        created = datetime(2025, 1, 19, 9, 0, 0)
        # when
        result = TimeService.estimated_finish_time(created)
        # then
        assert result == created + timedelta(hours=9)

    def test_get_total_time_spent_returns_hours_and_minutes(self) -> None:
        # given
        start = datetime(2025, 1, 19, 9, 0, 0)
        end = datetime(2025, 1, 19, 10, 15, 0)

        # when
        hours, minutes = TimeService.get_total_time_spent(start, end)

        # then
        assert (hours, minutes) == (1, 15)

    def test_get_start_time_success(self) -> None:
        # given
        lines = [
            "**Date:** 2025-01-19\n",
            "**Start Time:** 09:30:00\n",
        ]

        # when
        index, created_time = TimeService.get_start_time(lines)

        # then
        assert index == 1
        assert created_time == datetime(2025, 1, 19, 9, 30, 0)

    def test_get_start_time_missing_raises(self) -> None:
        # when
        with raises(ValueError):
            # then
            TimeService.get_start_time(["No date\n", "No start\n"])

    def test_get_daily_related_names_and_week_folder_file(
        self,
        mocker: MockerFixture,
    ) -> None:
        # given
        mocker.patch("taskjournal.services.time.TEMPLATE_FORMAT", "md")
        # when
        target = datetime(2025, 1, 19, 9, 0, 0)

        # then
        assert TimeService.get_daily_notes_name(target) == "2025-01-19-DailyNotes.md"
        assert TimeService.get_1on1_name(target) == "2025-01-19-1on1.md"

        mocker.patch("taskjournal.services.time.BASE_DIR", "/tmp/base")
        mocker.patch(
            "taskjournal.services.time.FileService.get_week_folder",
            return_value="/tmp/base/2025/week3",
        )
        makedirs = mocker.patch("taskjournal.services.time.os.makedirs")

        daily_file, week_folder = TimeService.get_week_folder_and_daily_notes_file(target)

        assert week_folder == "/tmp/base/2025/week3"
        assert daily_file == "/tmp/base/2025/week3/2025-01-19-DailyNotes.md"
        makedirs.assert_called_once_with("/tmp/base/2025/week3", exist_ok=True)
