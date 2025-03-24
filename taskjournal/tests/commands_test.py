import os
from unittest.mock import patch, mock_open
from freezegun import freeze_time
from taskjournal.commands import write_to_file, create_daily_notes_file, finalize_daily_notes, create_week_summary, \
    create_retro_file


@patch("builtins.open", new_callable=mock_open)
def test_write_to_file(mock_file):
    # Given
    file_path = "test.txt"
    content = "Hello, world!"
    # When
    write_to_file(file_path, content)
    # Then
    mock_file.assert_called_once_with(file_path, "w")
    mock_file().write.assert_called_once_with(content)


@freeze_time("2025-01-19 10:00:00")
@patch("builtins.open", new_callable=mock_open, read_data="Template with {{creation_time}} and {{tasks}}.")
def test_create_daily_notes_file(mock_file, daily_notes_template):
    # Given
    file_path = "daily_notes.txt"
    # When
    create_daily_notes_file(file_path, daily_notes_template)
    # Then
    mock_file.assert_any_call(file_path, "w")
    # Verify the written content
    written_content = mock_file().write.call_args[0][0]
    assert "2025-01-19 10:00:00" in written_content
    assert "[ ] Check emails" in written_content


@freeze_time("2025-01-19 18:00:00")
def test_finalize_daily_notes(mocker):
    # Given
    file_path = "fixtures/daily_notes.txt"
    write_finalize_file_mock = mocker.patch("taskjournal.commands.write_lines_to_file")
    write_end_of_file_mock = mocker.patch("taskjournal.commands.write_to_file")
    # When
    finalize_daily_notes(file_path)
    # Then
    lines = ['==== Daily Tasks Performed ===\n',
             '\n',
             'Start time: 2025-03-21 10:57:35\n',
             'Finalized: 2025-01-19 18:00:00\n',
             'Total Time Spent: -61 days, 7:02:25\n',
             '\n',
             'Sprint 27\n',
             '\n',
             'Tasks:\n',
             '[x] Check emails\n',
             '[x] [BE-111] migration database\n',
             '\n',
             '\n']
    write_finalize_file_mock.assert_called_once_with(file_path, lines)
    write_end_of_file_mock.assert_called_once()


def test_create_week_summary(base_dir, week_summary_template, mocker):
    # Given
    week_folder = "fixtures/"
    load_template_mock = mocker.patch("taskjournal.commands.load_template")
    write_to_file_mock = mocker.patch("taskjournal.commands.write_to_file")

    # When
    create_week_summary(week_folder, week_summary_template)

    # Then
    load_template_mock.assert_called_once()
    write_to_file_mock.assert_called_once()


@patch("os.path.exists", return_value=False)
def test_create_retro_file(week_folder, retro_template, mocker):
    # Given
    load_template_mock = mocker.patch("taskjournal.commands.load_template")
    write_content_mock = mocker.patch("taskjournal.commands.write_to_file")
    # When
    retro_file = create_retro_file(week_folder, retro_template)
    # Then
    expected_path = os.path.join(week_folder, "retro.txt")
    assert retro_file == expected_path
    load_template_mock.assert_called_once_with(retro_template)
    write_content_mock.assert_called_once()
