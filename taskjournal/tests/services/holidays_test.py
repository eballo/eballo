from datetime import date, timedelta

from pytest import fixture

from taskjournal.services.holidays import HolidayService


@fixture
def temp_holiday_file(tmp_path):
    """
    Creates a temporary holiday file for testing.
    Using pytest's built-in 'tmp_path' fixture is cleaner than tempfile.
    """
    # Local import as requested
    from textwrap import dedent

    # Given: A file structure with specific holidays
    content = dedent(
        """
    # From last year
    2026-01-02 - Old Holiday

    # National holidays
    2026-01-01 - New Year's Day
    2026-12-25 - Christmas

    # Malformed Section
    This is not a date
    """
    )

    file_path = tmp_path / "holidays.txt"
    file_path.write_text(content, encoding="utf-8")

    return str(file_path)


def test_holiday_loading_counts(temp_holiday_file):

    # Given
    filepath = temp_holiday_file

    # When
    service = HolidayService(filepath)

    # Then
    assert len(service.holidays) == 3
    assert len(service.categories) == 2


def test_category_assignment(temp_holiday_file):

    # Given
    service = HolidayService(temp_holiday_file)
    target_date = date(2026, 1, 2)

    # When
    holiday_info = service.is_holiday(target_date)

    # Then
    assert holiday_info is not None
    assert holiday_info["category"] == "From last year"
    assert holiday_info["description"] == "Old Holiday"


def test_check_specific_holiday_positive(temp_holiday_file):

    # Given
    service = HolidayService(temp_holiday_file)
    christmas = date(2026, 12, 25)

    # When
    result = service.is_holiday(christmas)

    # Then
    assert result is not None
    assert result["description"] == "Christmas"


def test_check_specific_holiday_negative(temp_holiday_file):

    # Given
    service = HolidayService(temp_holiday_file)
    regular_day = date(2026, 6, 15)

    # When
    result = service.is_holiday(regular_day)

    # Then
    assert result is None


def test_get_upcoming_holidays_logic(tmp_path):
    """
    We create a custom file here to ensure the dates are definitely in the future relative
    to execution time, ensuring the test is deterministic without complex time mocking.
    """

    # Given
    today = date.today()
    future_1 = today + timedelta(days=10)
    future_2 = today + timedelta(days=20)

    content = f"""
    # Future
    {future_1} - Near Future Holiday
    {future_2} - Far Future Holiday
    """

    file_path = tmp_path / "future_holidays.txt"
    file_path.write_text(content, encoding="utf-8")

    service = HolidayService(str(file_path))

    # When
    upcoming = service.get_upcoming_holidays(limit=1)

    # Then
    assert len(upcoming) == 1
    assert upcoming[0][0] == future_1
    assert upcoming[0][1]["description"] == "Near Future Holiday"
