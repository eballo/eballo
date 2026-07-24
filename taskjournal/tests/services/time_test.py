from datetime import datetime, timedelta

from freezegun import freeze_time
from pytest import raises
from pytest_mock import MockerFixture

from taskjournal.services.time import TimeService


class TestTime:

    @freeze_time("2025-01-20 12:00:00")
    def test_calculate_working_hours_valid(self, mocker: MockerFixture) -> None:
        # given — Monday, no prior days accumulated this week
        created_time = "2025-01-20 09:00:00"
        mock_open = mocker.mock_open(read_data=f"Start time: {created_time}\n")
        mocker.patch("builtins.open", mock_open)
        mocker.patch(
            "taskjournal.services.time.TimeService.get_start_time",
            return_value=(0, datetime.strptime(created_time, "%Y-%m-%d %H:%M:%S")),
        )
        mocker.patch("taskjournal.services.time.exists", return_value=False)

        # when
        created, elapsed, finish = TimeService.calculate_working_hours("notes.txt")

        # then
        assert created == datetime.strptime(created_time, "%Y-%m-%d %H:%M:%S")
        assert round(elapsed, 1) == 3.0
        assert finish == created + timedelta(hours=9, minutes=30)

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

    def test_get_expected_workday_seconds__mon_to_thu_is_8_5h(self) -> None:
        for day in (datetime(2025, 1, 20), datetime(2025, 1, 21), datetime(2025, 1, 22), datetime(2025, 1, 23)):
            assert TimeService.get_expected_workday_seconds(day) == int(8.5 * 3600)

    def test_get_expected_workday_seconds__friday_is_6h(self) -> None:
        friday = datetime(2025, 1, 24)
        assert TimeService.get_expected_workday_seconds(friday) == 6 * 3600

    def test_get_expected_week_seconds_before__monday_is_zero(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.services.time.exists", return_value=False)
        monday = datetime(2025, 1, 20, 9, 0, 0)
        assert TimeService.get_expected_week_seconds_before("/tmp/base/2025/week3", monday) == 0

    def test_get_expected_week_seconds_before__friday_sums_four_8_5h_days(self, mocker: MockerFixture) -> None:
        mocker.patch("taskjournal.services.time.exists", return_value=False)
        friday = datetime(2025, 1, 24, 9, 0, 0)
        assert TimeService.get_expected_week_seconds_before("/tmp/base/2025/week3", friday) == int(4 * 8.5 * 3600)

    def test_get_expected_week_seconds_before__holiday_day_counts_as_neutral_8h(
        self, mocker: MockerFixture
    ) -> None:
        # Monday is a holiday (marker file exists) → counted as 8h instead of 8.5h
        mocker.patch(
            "taskjournal.services.time.exists",
            side_effect=lambda path: "Holidays" in path,
        )
        tuesday = datetime(2025, 1, 21, 9, 0, 0)
        result = TimeService.get_expected_week_seconds_before("/tmp/base/2025/week3", tuesday)
        assert result == 8 * 3600

    def test_estimated_finish_time__monday_no_accumulated(self, mocker: MockerFixture) -> None:
        # Monday, 0 days before → expected=0, extra=0, today=8.5h work + 1h break
        mocker.patch("taskjournal.services.time.exists", return_value=False)
        created = datetime(2025, 1, 20, 9, 0, 0)
        result = TimeService.estimated_finish_time(created, "/tmp/base/2025/week3", accumulated_seconds=0)
        assert result == created + timedelta(hours=9, minutes=30)

    def test_estimated_finish_time__ahead_of_schedule(self, mocker: MockerFixture) -> None:
        # Friday, expected=4*8.5h=34h, accumulated=36h, extra=+2h → today=6h(cap)-2h=4h + 0h break
        mocker.patch("taskjournal.services.time.exists", return_value=False)
        created = datetime(2025, 1, 24, 9, 0, 0)
        accumulated = 36 * 3600
        result = TimeService.estimated_finish_time(created, "/tmp/base/2025/week3", accumulated_seconds=accumulated)
        assert result == created + timedelta(hours=4)

    def test_estimated_finish_time__behind_schedule(self, mocker: MockerFixture) -> None:
        # Friday, expected=34h, accumulated=28h, extra=-6h → today=6h (capped) + 0h break
        mocker.patch("taskjournal.services.time.exists", return_value=False)
        created = datetime(2025, 1, 24, 9, 0, 0)
        accumulated = 28 * 3600
        result = TimeService.estimated_finish_time(created, "/tmp/base/2025/week3", accumulated_seconds=accumulated)
        assert result == created + timedelta(hours=6)

    def test_estimated_finish_time__friday_over_target_finishes_immediately(
        self, mocker: MockerFixture
    ) -> None:
        # So far ahead that today's work = 0, and Friday has no break to clamp to
        mocker.patch("taskjournal.services.time.exists", return_value=False)
        created = datetime(2025, 1, 24, 9, 0, 0)
        accumulated = 42 * 3600  # 8h extra over expected 34h
        result = TimeService.estimated_finish_time(created, "/tmp/base/2025/week3", accumulated_seconds=accumulated)
        assert result == created

    def test_estimated_finish_time__monday_over_target_clamps_to_break(
        self, mocker: MockerFixture
    ) -> None:
        # Monday-Thursday still keep the 1h break as a floor even when far ahead of schedule
        mocker.patch("taskjournal.services.time.exists", return_value=False)
        created = datetime(2025, 1, 21, 9, 0, 0)  # Tuesday
        accumulated = 20 * 3600  # way more than the 8.5h expected before Tuesday
        result = TimeService.estimated_finish_time(created, "/tmp/base/2025/week3", accumulated_seconds=accumulated)
        assert result == created + timedelta(hours=1)

    def test_get_total_time_spent_deducts_lunch(self) -> None:
        # 9h elapsed - 1h lunch = 8h worked
        start = datetime(2025, 1, 19, 9, 0, 0)
        end = datetime(2025, 1, 19, 18, 0, 0)

        hours, minutes = TimeService.get_total_time_spent(start, end)

        assert (hours, minutes) == (8, 0)

    def test_get_total_time_spent_clamps_to_zero(self) -> None:
        # Less than 1h elapsed → 0h worked (lunch already consumed the time)
        start = datetime(2025, 1, 19, 9, 0, 0)
        end = datetime(2025, 1, 19, 9, 30, 0)

        hours, minutes = TimeService.get_total_time_spent(start, end)

        assert (hours, minutes) == (0, 0)

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
        makedirs = mocker.patch("taskjournal.services.time.makedirs")

        daily_file, week_folder = TimeService.get_week_folder_and_daily_notes_file(target)

        assert week_folder == "/tmp/base/2025/week3"
        assert daily_file == "/tmp/base/2025/week3/2025-01-19-DailyNotes.md"
        makedirs.assert_called_once_with("/tmp/base/2025/week3", exist_ok=True)

    def test_resolve_daily_notes_file_does_not_create_directory(
        self,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("taskjournal.services.time.TEMPLATE_FORMAT", "md")
        mocker.patch("taskjournal.services.time.BASE_DIR", "/tmp/base")
        mocker.patch(
            "taskjournal.services.time.FileService.get_week_folder",
            return_value="/tmp/base/2025/week3",
        )
        makedirs = mocker.patch("taskjournal.services.time.makedirs")
        target = datetime(2025, 1, 19, 9, 0, 0)

        daily_file, week_folder = TimeService.resolve_daily_notes_file(target)

        assert week_folder == "/tmp/base/2025/week3"
        assert daily_file == "/tmp/base/2025/week3/2025-01-19-DailyNotes.md"
        makedirs.assert_not_called()

    def test_get_accumulated_week_seconds_returns_zero_on_monday(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("taskjournal.services.time.TEMPLATE_FORMAT", "md")
        mocker.patch("taskjournal.services.time.BASE_DIR", "/tmp/base")
        mocker.patch(
            "taskjournal.services.time.FileService.get_week_folder",
            return_value="/tmp/base/2025/week3",
        )
        mocker.patch("taskjournal.services.time.makedirs")
        today = datetime(2025, 1, 20)  # Monday
        result = TimeService.get_accumulated_week_seconds("/tmp/base/2025/week3", today)
        assert result == 0

    def test_get_accumulated_week_seconds_sums_previous_days(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("taskjournal.services.time.TEMPLATE_FORMAT", "md")
        mocker.patch("taskjournal.services.time.BASE_DIR", "/tmp/base")
        mocker.patch(
            "taskjournal.services.time.FileService.get_week_folder",
            return_value="/tmp/base/2025/week3",
        )
        mocker.patch("taskjournal.services.time.makedirs")
        mocker.patch(
            "taskjournal.services.time.exists",
            side_effect=lambda path: "Holidays" not in path,
        )
        mocker.patch(
            "taskjournal.services.time.TimeService.get_total_time_from_daily_notes",
            return_value=3600,
        )
        today = datetime(2025, 1, 22)  # Wednesday — 2 days before (Mon, Tue)
        result = TimeService.get_accumulated_week_seconds("/tmp/base/2025/week3", today)
        assert result == 7200  # 2 x 3600

    def test_get_accumulated_week_seconds_holiday_day_counts_as_neutral_8h(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("taskjournal.services.time.TEMPLATE_FORMAT", "md")
        mocker.patch("taskjournal.services.time.BASE_DIR", "/tmp/base")
        mocker.patch(
            "taskjournal.services.time.FileService.get_week_folder",
            return_value="/tmp/base/2025/week3",
        )
        mocker.patch("taskjournal.services.time.makedirs")
        # Monday is a holiday (marker file exists); Tuesday has no notes at all.
        mocker.patch(
            "taskjournal.services.time.exists",
            side_effect=lambda path: "Holidays" in path and "2025-01-20" in path,
        )
        wednesday = datetime(2025, 1, 22)
        result = TimeService.get_accumulated_week_seconds("/tmp/base/2025/week3", wednesday)
        assert result == 8 * 3600

    def test_get_accumulated_week_seconds_skips_missing_files(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("taskjournal.services.time.TEMPLATE_FORMAT", "md")
        mocker.patch("taskjournal.services.time.BASE_DIR", "/tmp/base")
        mocker.patch(
            "taskjournal.services.time.FileService.get_week_folder",
            return_value="/tmp/base/2025/week3",
        )
        mocker.patch("taskjournal.services.time.makedirs")
        mocker.patch("taskjournal.services.time.exists", return_value=False)
        today = datetime(2025, 1, 24)  # Friday — Mon-Thu before today
        result = TimeService.get_accumulated_week_seconds("/tmp/base/2025/week3", today)
        assert result == 0

    def test_get_accumulated_week_seconds_continues_on_parse_error(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("taskjournal.services.time.TEMPLATE_FORMAT", "md")
        mocker.patch("taskjournal.services.time.BASE_DIR", "/tmp/base")
        mocker.patch(
            "taskjournal.services.time.FileService.get_week_folder",
            return_value="/tmp/base/2025/week3",
        )
        mocker.patch("taskjournal.services.time.makedirs")
        mocker.patch(
            "taskjournal.services.time.exists",
            side_effect=lambda path: "Holidays" not in path,
        )
        mocker.patch(
            "taskjournal.services.time.TimeService.get_total_time_from_daily_notes",
            side_effect=ValueError("bad file"),
        )
        today = datetime(2025, 1, 22)  # Wednesday
        result = TimeService.get_accumulated_week_seconds("/tmp/base/2025/week3", today)
        assert result == 0
