from datetime import date
from textwrap import dedent

from pytest import fixture

from taskjournal.services.working_days import WorkingDaysService


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@fixture
def mock_year_structure(tmp_path, mocker):
    """
    Sets up a temporary directory structure mimicking the real app:
    tmp_path/
      └── 2026/
          └── holidays.txt

    It patches 'taskjournal.config.BASE_DIR' to point to this tmp_path.
    """
    year = "2026"
    year_dir = tmp_path / year
    year_dir.mkdir()

    # 1. Create a holiday file with specific test cases
    # 2026-01-01 is a Thursday (Weekday Holiday)
    # 2026-01-03 is a Saturday (Weekend Holiday - should be counted as weekend)
    # 2026-01-06 is a Tuesday (Weekday Holiday)
    content = dedent(
        """
        # Weekday Holiday
        2026-01-01 - New Year

        # Weekend Holiday (Saturday)
        2026-01-03 - Weekend Holiday

        # Another Weekday Holiday
        2026-01-06 - Epiphany
        """
    )

    holiday_file = year_dir / "holidays.txt"
    holiday_file.write_text(content, encoding="utf-8")

    # 2. Patch BASE_DIR so the service looks in our temp folder
    # Assuming 'taskjournal.services.working_days' imports BASE_DIR from config
    mocker.patch("taskjournal.services.working_days.BASE_DIR", str(tmp_path))

    # We also need to patch HOLIDAYS_FILE if it's imported,
    # but usually patching the config attribute is safer if imported directly.
    # Here we assume the service does: from taskjournal.config import BASE_DIR, HOLIDAYS_FILE
    # If the service imports variables directly, we must patch where they are USED.
    mocker.patch("taskjournal.services.working_days.HOLIDAYS_FILE", "holidays.txt")

    return year


@fixture
def mock_today(mocker):
    """
    Mocks datetime.today() to return a fixed date (2026-01-10).
    This ensures get_progress() is deterministic.
    """

    # Create a fake class that behaves like datetime.date
    class MockDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 1, 10)

    # Patch the 'datetime' imported in the service module
    # Note: The service imports it as: from datetime import date as datetime
    mocker.patch("taskjournal.services.working_days.datetime", MockDate)

    return date(2026, 1, 10)


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


def test_initialization_loads_holidays(mock_year_structure):
    # Given
    year = mock_year_structure

    # When
    service = WorkingDaysService(year)

    # Then
    # We verify the internal holiday service loaded the 3 dates from our fixture
    assert len(service.holiday_service.holidays) == 3


def test_summary_calculation(mock_year_structure):
    # Given
    year = mock_year_structure
    service = WorkingDaysService(year)

    # When
    summary = service.summary()

    # Then
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


def test_get_progress_logic(mock_year_structure, mock_today):
    # Given
    year = mock_year_structure
    service = WorkingDaysService(year)

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

    # When
    progress = service.get_progress()

    # Then
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


def test_get_real_working_days_return_int(mock_year_structure):
    # Given
    service = WorkingDaysService(mock_year_structure)

    # When
    result = service.get_real_working_days()

    # Then
    assert isinstance(result, int)
    assert result == 259  # Based on 2026 calendar logic verified above


def test_missing_days_calculation(mock_year_structure, mock_today):
    """
    Verifies that days in the future are counted as 'missing' or 'remaining'.
    """
    # Given
    service = WorkingDaysService(mock_year_structure)

    # When
    progress = service.get_progress()

    # Then
    # Total real working days (259) - Worked (5) = 254
    assert progress["missing"] == 254

    # Total holidays on weekdays (2) - Taken (2) = 0 remaining
    # (Because Jan 1 and Jan 6 are passed by Jan 10)
    assert progress["holidays_remaining"] == 0
