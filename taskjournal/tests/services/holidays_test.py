from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

from pytest_mock import MockerFixture

from taskjournal.services.holidays import HolidayService


class TestHolidays:

    def test_holiday_loading_counts(
        self,
        temp_holiday_file: str,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:

        # given
        filepath = temp_holiday_file

        # when
        service = holiday_service_factory(filepath)

        # then
        assert len(service.holidays) == 3
        assert len(service.categories) == 2

    def test_category_assignment(
        self,
        temp_holiday_file: str,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:

        # given
        service = holiday_service_factory(temp_holiday_file)
        target_date = date(2026, 1, 2)

        # when
        holiday_info = service.is_holiday(target_date)

        # then
        assert holiday_info is not None
        assert isinstance(holiday_info, dict)
        assert holiday_info["category"] == "From last year"
        assert holiday_info["description"] == "Old Holiday"

    def test_check_specific_holiday_positive(
        self,
        temp_holiday_file: str,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:

        # given
        service = holiday_service_factory(temp_holiday_file)
        christmas = date(2026, 12, 25)

        # when
        result = service.is_holiday(christmas)

        # then
        assert result is not None
        assert isinstance(result, dict)
        assert result["description"] == "Christmas"

    def test_check_specific_holiday_negative(
        self,
        temp_holiday_file: str,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:

        # given
        service = holiday_service_factory(temp_holiday_file)
        regular_day = date(2026, 6, 15)

        # when
        result = service.is_holiday(regular_day)

        # then
        assert result is None

    def test_get_upcoming_holidays_logic(
        self,
        tmp_path: Path,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:
        # given
        """
        We create a custom file here to ensure the dates are definitely in the future relative
        to execution time, ensuring the test is deterministic without complex time mocking.
        """

        # when
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

        service = holiday_service_factory(str(file_path))

        upcoming = service.get_upcoming_holidays(limit=1)

        # then
        assert len(upcoming) == 1
        assert upcoming[0][0] == future_1
        assert upcoming[0][1]["description"] == "Near Future Holiday"

    def test_populate_files_generates_markdown(
        self,
        temp_holiday_file: str,
        tmp_path: Path,
        mocker: MockerFixture,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:
        # given
        service = holiday_service_factory(temp_holiday_file)

        # We mock 'get_week_folder' to return a subdirectory inside our test 'tmp_path'.
        # This prevents the test from trying to write to the real BASE_DIR.
        fake_week_dir = tmp_path / "mock_week_folder"

        # Patch where the function is USED (imported), not where it is defined
        mocker.patch(
            "taskjournal.services.holidays.get_week_folder",
            return_value=str(fake_week_dir),
        )

        # when
        service.populate_files()

        # 1. Verify the directory was created
        # then
        assert fake_week_dir.exists()

        # 2. Verify a specific file was created (2026-01-01 from temp_holiday_file)
        expected_file = fake_week_dir / "2026-01-01-DailyNotes-Holidays.md"
        assert expected_file.exists()

        # 3. Verify the file content matches the service logic
        content = expected_file.read_text(encoding="utf-8")
        assert "Category: National holidays" in content
        assert "Description: New Year's Day" in content

        # 4. Verify correct number of files (3 valid dates in temp_holiday_file)
        generated_files = list(fake_week_dir.glob("*.md"))
        assert len(generated_files) == 3

    def test_load_and_parse_missing_file_logs_with_print(
        self,
        mocker: MockerFixture,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:
        # given
        mocked_print = mocker.patch("builtins.print")

        # when
        service = holiday_service_factory("missing-file-path.md")

        # then
        assert service.holidays == {}
        mocked_print.assert_called_once()

    def test_load_and_parse_invalid_date_value_error_prints_warning(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:
        # given
        file_path = tmp_path / "holidays.txt"
        file_path.write_text("2026-01-01 - New Year\n", encoding="utf-8")

        class FakeDate:
            @staticmethod
            def fromisoformat(_value: str) -> date:
                raise ValueError("bad date")

            @staticmethod
            def today() -> date:
                return date(2026, 1, 1)

        mocker.patch("taskjournal.services.holidays.datetime", FakeDate)
        mocked_print = mocker.patch("builtins.print")

        # when
        service = holiday_service_factory(str(file_path))

        # then
        assert service.holidays == {}
        mocked_print.assert_called_once_with(
            "Warning: Invalid date format found: 2026-01-01"
        )

    def test_get_past_holidays_logic(
        self,
        tmp_path: Path,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:
        # given
        today = date.today()
        past_1 = today - timedelta(days=20)
        past_2 = today - timedelta(days=10)
        future = today + timedelta(days=10)

        content = f"""
        # History
        {past_1} - Old Holiday
        {past_2} - Recent Past Holiday
        {future} - Future Holiday
        """

        file_path = tmp_path / "past_holidays.txt"
        file_path.write_text(content, encoding="utf-8")

        # when
        service = holiday_service_factory(str(file_path))
        past = service.get_past_holidays()

        # then
        assert len(past) == 2
        assert past[0][0] == past_1
        assert past[1][0] == past_2
        assert past[0][1]["description"] == "Old Holiday"
        assert past[1][1]["description"] == "Recent Past Holiday"

    def test_summary_logic_calculations(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:
        # given
        today = date.today()
        past_date = today - timedelta(days=5)
        future_date = today + timedelta(days=5)

        content = f"""
        # Test
        {past_date} - Past
        {today} - Today
        {future_date} - Future
        """
        file_path = tmp_path / "summary_test.txt"
        file_path.write_text(content, encoding="utf-8")
        service = holiday_service_factory(str(file_path))
        logger = mocker.patch("taskjournal.services.holidays.logger")

        # when
        service.summary()

        # then
        # Total: 3, Done: 1 (33.3%), Remaining: 2
        logger.info.assert_any_call("Total holidays: 3")
        logger.info.assert_any_call("Done:      1 (33.3%)")
        logger.info.assert_any_call("Remaining:      2")

    def test_summary_methods_output_format(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:
        # given
        today = date.today()
        past_date = today - timedelta(days=5)
        future_date = today + timedelta(days=5)

        # Use different lengths for descriptions to test alignment
        content = f"""
        # Test
        {past_date} - Short
        {future_date} - Very Long Description
        """
        file_path = tmp_path / "alignment_test.txt"
        file_path.write_text(content, encoding="utf-8")
        service = holiday_service_factory(str(file_path))
        logger = mocker.patch("taskjournal.services.holidays.logger")

        # when
        service.summary_all()

        # then
        # Check for status indicators and alignment
        # max_desc_len should be len("Very Long Description") = 21
        # Short description should be padded: "Short                "
        logger.info.assert_any_call(f"[x] {past_date} : Short                 [Test]")
        logger.info.assert_any_call(f"[ ] {future_date} : Very Long Description [Test]")

    def test_summary_methods_emit_logs(
        self,
        temp_holiday_file: str,
        mocker: MockerFixture,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:
        # given
        logger = mocker.patch("taskjournal.services.holidays.logger")
        # when
        service = holiday_service_factory(temp_holiday_file)

        service.summary_upcoming(limit=2)
        service.summary_all()

        # then
        assert logger.info.call_count > 2

    def test_populate_files_logs_write_errors(
        self,
        temp_holiday_file: str,
        tmp_path: Path,
        mocker: MockerFixture,
        holiday_service_factory: Callable[[str], HolidayService],
    ) -> None:
        # given
        service = holiday_service_factory(temp_holiday_file)
        mocker.patch(
            "taskjournal.services.holidays.get_week_folder", return_value=str(tmp_path)
        )
        mocker.patch("builtins.open", side_effect=OSError("disk full"))
        logger = mocker.patch("taskjournal.services.holidays.logger")

        # when
        service.populate_files()

        # then
        assert logger.error.call_count >= 1
