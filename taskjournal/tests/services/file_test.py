from pytest_mock import MockerFixture

from os.path import join
from datetime import datetime

from pytest import raises

from taskjournal.services.file import FileService


class TestFile:

    def test_get_week_folder(self, base_dir: str, mocker: MockerFixture) -> None:
        # given
        mock_datetime = mocker.patch("taskjournal.commands.commands.datetime")
        mock_datetime.now.return_value = datetime(2025, 1, 19)
        # when
        date = mock_datetime.now()
        expected_folder = join(base_dir, "2025", "week3")
        # then
        assert FileService.get_week_folder(base_dir, date) == expected_folder

    def test_get_week_folder__uses_iso_year_at_year_boundary(
        self, base_dir: str
    ) -> None:
        # 2025-12-29 is a Monday belonging to ISO week 1 of ISO-year 2026.
        date = datetime(2025, 12, 29)
        expected_folder = join(base_dir, "2026", "week1")
        assert FileService.get_week_folder(base_dir, date) == expected_folder

    def test_write_to_file(self, mocker: MockerFixture) -> None:
        # given
        mock_file = mocker.mock_open()
        mocker.patch("builtins.open", mock_file)
        file_path = "test.txt"
        content = "Hello, world!"
        # when
        FileService.write_to_file(file_path, content)
        # then
        mock_file.assert_called_once_with(file_path, "w")
        mock_file().write.assert_called_once_with(content)

    def test_write_lines_to_file(self, mocker: MockerFixture) -> None:
        # given
        mock_file = mocker.mock_open()
        mocker.patch("builtins.open", mock_file)
        file_path = "test.txt"
        lines = ["Line 1\n", "Line 2\n"]

        # when
        FileService.write_lines_to_file(file_path, lines)

        # then
        mock_file.assert_called_once_with(file_path, "w")
        mock_file().writelines.assert_called_once_with(lines)

    def test_load_template_success(self, mocker: MockerFixture) -> None:
        # given
        mocker.patch("taskjournal.services.file.exists", return_value=True)
        mock_open_file = mocker.mock_open(read_data="template content")
        mocker.patch("builtins.open", mock_open_file)

        # when
        result = FileService.load_template("template.txt")

        # then
        assert result == "template content"
        mock_open_file.assert_called_once_with("template.txt", "r")

    def test_load_template_file_not_found(self, mocker: MockerFixture) -> None:
        # when
        mocker.patch("taskjournal.services.file.exists", return_value=False)

        # then
        with raises(FileNotFoundError):
            FileService.load_template("nonexistent.txt")

    def test_check_finalized_in_file_true(self, mocker: MockerFixture) -> None:
        # given
        mock_open = mocker.mock_open(read_data="Task 1\nFinalized: yes\nTask 2")
        mocker.patch("builtins.open", mock_open)

        # when
        result = FileService.check_finalized_in_file("test.txt")

        # then
        assert result is True

    def test_check_finalized_in_file_false(self, mocker: MockerFixture) -> None:
        # given
        mock_open = mocker.mock_open(read_data="Task 1\nTask 2")
        mocker.patch("builtins.open", mock_open)

        # when
        result = FileService.check_finalized_in_file("test.txt")
        # then
        assert result is False

    def test_check_finalized_in_file_file_not_found(
        self, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch("builtins.open", side_effect=FileNotFoundError())
        mock_logger = mocker.patch("taskjournal.services.file.logger")

        # when
        result = FileService.check_finalized_in_file("missing.txt")
        # then
        assert result is False
        mock_logger.error.assert_called_once_with(
            "File 'missing.txt' was not found."
        )

    def test_check_finalized_in_file_generic_exception(
        self, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch("builtins.open", side_effect=OSError("disk error"))
        mock_logger = mocker.patch("taskjournal.services.file.logger")

        # when
        result = FileService.check_finalized_in_file("test.txt")
        # then
        assert result is False
        mock_logger.error.assert_called_once()
        assert "disk error" in mock_logger.error.call_args[0][0]

    def test_check_finalized_in_file_end_time_with_value(self, mocker: MockerFixture) -> None:
        # given
        mock_open = mocker.mock_open(read_data="**End Time:** 20:00:00\n")
        mocker.patch("builtins.open", mock_open)

        # when
        result = FileService.check_finalized_in_file("test.txt")

        # then
        assert result is True

    def test_check_finalized_in_file_end_time_empty(self, mocker: MockerFixture) -> None:
        # given
        mock_open = mocker.mock_open(read_data="**End Time:** \n")
        mocker.patch("builtins.open", mock_open)

        # when
        result = FileService.check_finalized_in_file("test.txt")

        # then
        assert result is False

    def test_get_summary_from_daily_notes_markdown_heading(
        self,
        mocker: MockerFixture,
    ) -> None:
        # given
        data = "Header\n## 📋 Summary\nLine 1\nLine 2\n"
        mock_open = mocker.mock_open(read_data=data)
        mocker.patch("builtins.open", mock_open)

        # when
        result = FileService.get_summary_from_daily_notes("file.md")

        # then
        assert result == "Line 1\nLine 2"

    def test_get_summary_from_daily_notes_plain_heading(
        self, mocker: MockerFixture
    ) -> None:
        # given
        data = "Header\n📋 Summary\nOnly line\n"
        mock_open = mocker.mock_open(read_data=data)
        mocker.patch("builtins.open", mock_open)

        # when
        result = FileService.get_summary_from_daily_notes("file.md")

        # then
        assert result == "Only line"

    def test_get_summary_from_daily_notes_no_heading_returns_empty(
        self,
        mocker: MockerFixture,
    ) -> None:
        # given
        mock_open = mocker.mock_open(read_data="Header\nNo summary section\n")
        mocker.patch("builtins.open", mock_open)

        # when
        result = FileService.get_summary_from_daily_notes("file.md")

        # then
        assert result == ""
