import os
from datetime import datetime
from services.file import (
    get_week_folder,
    write_to_file,
    load_template,
    check_finalized_in_file,
)
from pytest import raises


def test_get_week_folder(base_dir, mocker):
    # Given
    mock_datetime = mocker.patch("taskjournal.commands.datetime")
    mock_datetime.now.return_value = datetime(2025, 1, 19)
    date = mock_datetime.now()
    expected_folder = os.path.join(base_dir, "2025", "week3")
    # Then / When
    assert get_week_folder(base_dir, date) == expected_folder


def test_write_to_file(mocker):
    # Given
    mock_file = mocker.mock_open()
    mocker.patch("builtins.open", mock_file)
    file_path = "test.txt"
    content = "Hello, world!"
    # When
    write_to_file(file_path, content)
    # Then
    mock_file.assert_called_once_with(file_path, "w")
    mock_file().write.assert_called_once_with(content)


from services.file import write_lines_to_file


def test_write_lines_to_file(mocker):
    # Given
    mock_file = mocker.mock_open()
    mocker.patch("builtins.open", mock_file)
    file_path = "test.txt"
    lines = ["Line 1\n", "Line 2\n"]

    # When
    write_lines_to_file(file_path, lines)

    # Then
    mock_file.assert_called_once_with(file_path, "w")
    mock_file().writelines.assert_called_once_with(lines)


def test_load_template_success(mocker):
    # Given
    mocker.patch("os.path.exists", return_value=True)
    mock_open_file = mocker.mock_open(read_data="template content")
    mocker.patch("builtins.open", mock_open_file)

    # When
    result = load_template("template.txt")

    # Then
    assert result == "template content"
    mock_open_file.assert_called_once_with("template.txt", "r")


def test_load_template_file_not_found(mocker):
    # Given
    mocker.patch("os.path.exists", return_value=False)

    # Then
    with raises(FileNotFoundError):
        load_template("nonexistent.txt")


def test_check_finalized_in_file_true(mocker):
    # Given
    mock_open = mocker.mock_open(read_data="Task 1\nFinalized: yes\nTask 2")
    mocker.patch("builtins.open", mock_open)

    # When
    result = check_finalized_in_file("test.txt")

    # Then
    assert result is True


def test_check_finalized_in_file_false(mocker):
    mock_open = mocker.mock_open(read_data="Task 1\nTask 2")
    mocker.patch("builtins.open", mock_open)

    result = check_finalized_in_file("test.txt")
    assert result is False


def test_check_finalized_in_file_file_not_found(mocker):
    mocker.patch("builtins.open", side_effect=FileNotFoundError())
    mock_logger = mocker.patch("services.file.logger")

    result = check_finalized_in_file("missing.txt")
    assert result is False
    mock_logger.error.assert_called_once_with(
        "Error: The file 'missing.txt' was not found."
    )


def test_check_finalized_in_file_generic_exception(mocker):
    mocker.patch("builtins.open", side_effect=OSError("disk error"))
    mock_logger = mocker.patch("services.file.logger")

    result = check_finalized_in_file("test.txt")
    assert result is False
    mock_logger.error.assert_called_once()
    assert "disk error" in mock_logger.error.call_args[0][0]
