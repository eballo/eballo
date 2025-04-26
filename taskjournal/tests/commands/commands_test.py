import os
from datetime import datetime

from freezegun import freeze_time
from pytest import raises

from taskjournal.commands.commands import (
    create_daily_notes_file,
    finalize_daily_notes,
    create_week_summary,
    create_retro_file,
)


@freeze_time("2025-03-21 10:00:00")
def test_create_daily_notes_file(daily_notes_template, mocker):
    mock_file = mocker.mock_open(
        read_data="Template with {{date}} {{time}} and {{tasks}}."
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
    assert "10:00:00" in written_content
    assert "[ ] Check emails" in written_content


@freeze_time("2025-03-21 18:00:00")
def test_finalize_daily_notes(fixture_path, mocker):
    # Given

    file_path = fixture_path / "daily_notes.txt"
    write_finalize_file_mock = mocker.patch(
        "taskjournal.commands.commands.write_lines_to_file"
    )
    write_end_of_file_mock = mocker.patch("taskjournal.commands.commands.write_to_file")
    # When
    finalize_daily_notes(file_path, None)
    # Then
    lines = [
        "📅 Daily Tasks Log\n",
        "\n",
        " Sprint: 27\n",
        " Date: 2025-03-21\n",
        " Start Time: 10:57:35\n",
        " End Time: 18:00\n",
        " Time Spent: 07:02\n",
        "\n",
        "\n",
        "✅ Planned Tasks\n",
        "\n",
        "[x] Check emails\n",
        "[x] [BE-111] migration database\n",
        "\n",
        "\n",
        "✍️ Notes:\n",
        "\n",
        "\n",
        "📋 Summary\n",
    ]
    write_finalize_file_mock.assert_called_once_with(file_path, lines)


@freeze_time("2025-03-21 18:00:00")
def test_finalize_daily_notes_with_final_date(fixture_path, mocker):
    # Given

    file_path = fixture_path / "daily_notes_with_final_date.txt"
    write_finalize_file_mock = mocker.patch(
        "taskjournal.commands.commands.write_lines_to_file"
    )

    # When
    finalize_daily_notes(file_path, None)
    # Then
    lines = [
        "📅 Daily Tasks Log\n",
        "\n",
        " Sprint: 27\n",
        " Date: 2025-03-21\n",
        " Start Time: 10:57:35\n",
        " End Time: 18:00\n",
        " Time Spent: 07:02\n",
        "\n",
        "\n",
        "✅ Planned Tasks\n",
        "\n",
        "[x] Check emails\n",
        "[x] [BE-111] migration database\n",
        "\n",
        "\n",
        "✍️ Notes:\n",
        "\n",
        "\n",
        "📋 Summary\n",
    ]
    write_finalize_file_mock.assert_called_once_with(file_path, lines)


@freeze_time("2025-03-21 18:00:00")
def test_finalize_daily_notes_with_final_date_custom_date(fixture_path, mocker):
    # Given

    file_path = fixture_path / "daily_notes_with_final_date.txt"
    write_finalize_file_mock = mocker.patch(
        "taskjournal.commands.commands.write_lines_to_file"
    )

    # When
    custom_date = datetime.strptime("2025-03-21 18:10", "%Y-%m-%d %H:%M")
    finalize_daily_notes(file_path, custom_date)
    # Then
    lines = [
        "📅 Daily Tasks Log\n",
        "\n",
        " Sprint: 27\n",
        " Date: 2025-03-21\n",
        " Start Time: 10:57:35\n",
        " End Time: 18:10\n",
        " Time Spent: 07:12\n",
        "\n",
        "\n",
        "✅ Planned Tasks\n",
        "\n",
        "[x] Check emails\n",
        "[x] [BE-111] migration database\n",
        "\n",
        "\n",
        "✍️ Notes:\n",
        "\n",
        "\n",
        "📋 Summary\n",
    ]
    write_finalize_file_mock.assert_called_once_with(file_path, lines)


def test_finalize_daily_notes_missing_start_time(mocker):
    mock_file = mocker.mock_open(
        read_data="No start time here",
    )
    mocker.patch("builtins.open", mock_file)
    mocker.patch(
        "taskjournal.commands.commands.check_finalized_in_file", return_value=False
    )
    with raises(ValueError, match="Creation date not found in the file."):
        finalize_daily_notes("some_path.txt", None)


def test_finalize_daily_notes_already_finalized(mocker):
    mocker.patch(
        "taskjournal.commands.commands.check_finalized_in_file", return_value=True
    )
    mock_logger = mocker.patch("taskjournal.commands.commands.logger")
    finalize_daily_notes("already_finalized.txt", None)
    mock_logger.info.assert_called_once_with(
        "File 'already_finalized.txt' is already finalized."
    )


def test_create_week_summary(base_dir, fixture_path, week_summary_template, mocker):
    # Given
    load_template_mock = mocker.patch("taskjournal.commands.commands.load_template")
    write_to_file_mock = mocker.patch("taskjournal.commands.commands.write_to_file")

    # When
    create_week_summary(fixture_path, week_summary_template)

    # Then
    load_template_mock.assert_called_once()
    write_to_file_mock.assert_called_once()


def test_create_retro_file(week_folder, retro_template, mocker):
    # Given
    mock_exists = mocker.patch("os.path.exists", return_value=False)
    load_template_mock = mocker.patch("taskjournal.commands.commands.load_template")
    write_content_mock = mocker.patch("taskjournal.commands.commands.write_to_file")
    # When
    retro_file = create_retro_file(week_folder, retro_template)
    # Then
    expected_path = os.path.join(week_folder, "retro.txt")
    assert retro_file == expected_path
    load_template_mock.assert_called_once_with(retro_template)
    write_content_mock.assert_called_once()


def test_create_retro_file_already_exists(week_folder, retro_template, mocker):
    mocker.patch("os.path.exists", return_value=True)
    write_mock = mocker.patch("taskjournal.commands.commands.write_to_file")
    retro_file = create_retro_file(week_folder, retro_template)
    assert retro_file == os.path.join(week_folder, "retro.txt")
    write_mock.assert_not_called()
