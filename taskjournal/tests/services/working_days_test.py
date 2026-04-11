from collections.abc import Callable
from datetime import date, datetime

from pytest import mark
from pytest_mock import MockerFixture

from taskjournal.services.working_days import WorkingDaysService


class TestWorkingDays:

    def test_initialization_loads_holidays(
        self,
        mock_year_structure: str,
        working_days_service_factory: Callable[[str], WorkingDaysService],
    ) -> None:
        # given
        year = mock_year_structure

        # when
        service = working_days_service_factory(year)

        # We verify the internal holiday service loaded the 3 dates from our fixture
        # then
        assert len(service.holiday_service.holidays) == 3

    def test_summary_calculation(
        self,
        mock_year_structure: str,
        working_days_service_factory: Callable[[str], WorkingDaysService],
    ) -> None:
        # given
        year = mock_year_structure
        # when
        service = working_days_service_factory(year)

        summary = service.summary()

        # then
        assert summary["year"] == "2026"
        assert summary["total_calendar_days"] == 365

        # In 2026:
        # Jan 1 (Thu) -> Holiday
        # Jan 2 (Fri) -> Workday
        # Jan 3 (Sat) -> Weekend (Note: Our file lists this as holiday, but code prioritizes Weekend logic)
        # Jan 4 (Sun) -> Weekend
        # Jan 5 (Mon) -> Workday
        # Jan 6 (Tue) -> Holiday

        # Verify holidays_on_weekdays (should be 2: Jan 1 and Jan 6. Jan 3 is hidden by Weekend)
        assert summary["holidays_on_weekdays"] == 2

        # 2026 has 52 weeks + 1 day = 104 weekend days
        assert summary["total_weekends"] == 104

        # Real working days = Total - Weekends - WeekdayHolidays
        # 365 - 104 - 2 = 259
        assert summary["real_working_days"] == 259

    @mark.usefixtures("mock_today")
    def test_get_progress_logic(
        self,
        mock_year_structure: str,
        working_days_service_factory: Callable[[str], WorkingDaysService],
    ) -> None:
        # given
        year = mock_year_structure
        # when
        service = working_days_service_factory(year)

        # Mock date is set to 2026-01-10 via fixture
        # Let's manually calculate expected state for first 10 days of Jan 2026:
        # 1 Thu (Hol)
        # 2 Fri (Work)
        # 3 Sat (Weekend/Hol)
        # 4 Sun (Weekend)
        # 5 Mon (Work)
        # 6 Tue (Hol)
        # 7 Wed (Work)
        # 8 Thu (Work)
        # 9 Fri (Work)
        # 10 Sat (Weekend) <- Today

        progress = service.get_progress()

        # then
        assert progress["current_day_number"] == 10

        # Worked: Jan 2, 5, 7, 8, 9 (Total 5)
        assert progress["worked"] == 5

        # Holidays taken: Jan 1, Jan 6 (Total 2)
        assert progress["holidays_taken"] == 2

        # Weekends taken: Jan 3, 4, 10 (Total 3)
        assert progress["weekends_taken"] == 3

        # Percentage calculation
        # Total workdays for year = 259 (calculated in previous test)
        # 5 / 259 * 100
        expected_percent = round((5 / 259) * 100, 2)
        assert progress["progress_percentage"] == expected_percent

    def test_get_real_working_days_return_int(
        self,
        mock_year_structure: str,
        working_days_service_factory: Callable[[str], WorkingDaysService],
    ) -> None:
        # given
        service = working_days_service_factory(mock_year_structure)

        # when
        result = service.get_real_working_days()

        # then
        assert isinstance(result, int)
        assert result == 259  # Based on 2026 calendar logic verified above

    @mark.usefixtures("mock_today")
    def test_missing_days_calculation(
        self,
        mock_year_structure: str,
        working_days_service_factory: Callable[[str], WorkingDaysService],
    ) -> None:
        # given
        """
        Verifies that days in the future are counted as 'missing' or 'remaining'.
        """
        # when
        service = working_days_service_factory(mock_year_structure)

        progress = service.get_progress()

        # Total real working days (259) - Worked (5) = 254
        # then
        assert progress["missing"] == 254

        # Total holidays on weekdays (2) - Taken (2) = 0 remaining
        # (Because Jan 1 and Jan 6 are passed by Jan 10)
        assert progress["holidays_remaining"] == 0

    def test_get_progress_handles_zero_total_workdays(
        self,
        mocker: MockerFixture,
        working_days_service_factory: Callable[[str], WorkingDaysService],
    ) -> None:
        # given
        service = working_days_service_factory("2026")
        mocker.patch.object(
            service,
            "_analyze_year",
            return_value=[
                {"date": date(2026, 1, 1), "type": "holiday"},
                {"date": date(2026, 1, 2), "type": "weekend"},
            ],
        )

        class MockDate(date):
            @classmethod
            def today(cls) -> "MockDate":
                return cls(2025, 12, 31)

        mocker.patch("taskjournal.services.working_days.datetime", MockDate)

        # when
        progress = service.get_progress()

        # then
        assert progress["total_workdays"] == 0
        assert progress["progress_percentage"] == 0.0
        assert progress["holidays_remaining"] == 1

    def test_get_progress_ignores_unknown_entry_type(
        self,
        mocker: MockerFixture,
        working_days_service_factory: Callable[[str], WorkingDaysService],
    ) -> None:
        # given
        service = working_days_service_factory("2026")
        mocker.patch.object(
            service,
            "_analyze_year",
            return_value=[
                {"date": date(2026, 1, 1), "type": "unknown"},
                {"date": date(2026, 1, 2), "type": "weekend"},
            ],
        )

        class MockDate(date):
            @classmethod
            def today(cls) -> "MockDate":
                return cls(2026, 1, 2)

        mocker.patch("taskjournal.services.working_days.datetime", MockDate)

        # when
        progress = service.get_progress()

        # then
        assert progress["weekends_taken"] == 1
        assert progress["worked"] == 0

    def test_get_week_stats(
        self,
        mocker: MockerFixture,
        working_days_service_factory: Callable[[str], WorkingDaysService],
    ) -> None:
        # given
        service = working_days_service_factory("2025")
        custom_date = datetime(2025, 1, 15)  # Wednesday
        week_folder = "/dummy/path"

        # Mon: 2025-01-13
        # Tue: 2025-01-14
        # Wed: 2025-01-15
        # Thu: 2025-01-16
        # Fri: 2025-01-17

        # Mock get_daily_notes_name
        mocker.patch(
            "taskjournal.services.working_days.get_daily_notes_name",
            side_effect=lambda d: f"{d.strftime('%Y-%m-%d')}-DailyNotes.md",
        )

        # Mock os.path.exists to return True for Mon and Tue
        mocker.patch(
            "taskjournal.services.working_days.os.path.exists",
            side_effect=lambda p: "2025-01-13" in p or "2025-01-14" in p,
        )

        # Mock get_total_time_from_daily_notes
        mocker.patch(
            "taskjournal.services.working_days.get_total_time_from_daily_notes",
            side_effect=[3600, 1800],
        )

        # Mock DailyParserService.parse
        mock_data_mon = {"work_from": "office"}
        mock_data_tue = {"work_from": "home"}
        mocker.patch(
            "taskjournal.services.working_days.DailyParserService.parse",
            side_effect=[mock_data_mon, mock_data_tue],
        )

        # when
        stats = service.get_week_stats(custom_date, week_folder)

        # then
        assert stats["start_date"].date() == date(2025, 1, 13)
        assert stats["end_date"].date() == date(2025, 1, 17)
        assert stats["total_time_seconds"] == 5400  # 3600 + 1800
        assert stats["total_worked_days"] == 2
        assert stats["vacation_days"] == 3  # Wed, Thu, Fri missing
        assert stats["days_at_office"] == 1
        assert stats["days_at_home"] == 1
