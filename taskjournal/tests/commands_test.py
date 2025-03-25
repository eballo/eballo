import os
from pytest import raises
from freezegun import freeze_time
from taskjournal.commands import (
    create_daily_notes_file,
    finalize_daily_notes,
    create_week_summary,
    create_retro_file,
)


@freeze_time("2025-01-19 10:00:00")
def test_create_daily_notes_file(daily_notes_template, mocker):
    mock_file = mocker.mock_open(
        read_data="Template with {{creation_time}} and {{tasks}}."
    )
    mocker.patch("builtins.open", mock_file)
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
def test_finalize_daily_notes(fixture_path, mocker):
    # Given

    file_path = fixture_path / "daily_notes.txt"
    write_finalize_file_mock = mocker.patch("taskjournal.commands.write_lines_to_file")
    write_end_of_file_mock = mocker.patch("taskjournal.commands.write_to_file")
    # When
    finalize_daily_notes(file_path)
    # Then
    lines = [
        "==== Daily Tasks Performed ===\n",
        "\n",
        "Start time: 2025-03-21 10:57:35\n",
        "Finalized: 2025-01-19 18:00:00\n",
        "Total Time Spent: -61 days, 7:02:25\n",
        "\n",
        "Sprint 27\n",
        "\n",
        "Tasks:\n",
        "[x] Check emails\n",
        "[x] [BE-111] migration database\n",
    ]
    write_finalize_file_mock.assert_called_once_with(file_path, lines)
    write_end_of_file_mock.assert_called_once()


def test_finalize_daily_notes_missing_start_time(mocker):
    mock_file = mocker.mock_open(
        read_data="No start time here",
    )
    mocker.patch("builtins.open", mock_file)
    mocker.patch("taskjournal.commands.check_finalized_in_file", return_value=False)
    with raises(ValueError, match="Creation date not found in the file."):
        finalize_daily_notes("some_path.txt")


def test_create_week_summary(base_dir, fixture_path, week_summary_template, mocker):
    # Given
    load_template_mock = mocker.patch("taskjournal.commands.load_template")
    write_to_file_mock = mocker.patch("taskjournal.commands.write_to_file")

    # When
    create_week_summary(fixture_path, week_summary_template)

    # Then
    load_template_mock.assert_called_once()
    write_to_file_mock.assert_called_once()


def test_create_retro_file(week_folder, retro_template, mocker):
    # Given
    mock_exists = mocker.patch("os.path.exists", return_value=False)
    load_template_mock = mocker.patch("taskjournal.commands.load_template")
    write_content_mock = mocker.patch("taskjournal.commands.write_to_file")
    # When
    retro_file = create_retro_file(week_folder, retro_template)
    # Then
    expected_path = os.path.join(week_folder, "retro.txt")
    assert retro_file == expected_path
    load_template_mock.assert_called_once_with(retro_template)
    write_content_mock.assert_called_once()
