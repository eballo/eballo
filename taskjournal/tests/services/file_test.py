import os
from datetime import datetime
from services.file import get_week_folder, write_to_file


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
