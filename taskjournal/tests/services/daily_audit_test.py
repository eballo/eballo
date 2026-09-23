from datetime import date, datetime
from unittest.mock import MagicMock, call, patch

from pytest import mark

from taskjournal.models.parsed_note import ParsedNote
from taskjournal.services.daily_audit import DailyAuditService


def make_audit(tmp_path) -> DailyAuditService:
    return DailyAuditService(MagicMock(), MagicMock(), MagicMock(), str(tmp_path), "md")


@mark.parametrize("error", [ValueError, FileNotFoundError])
def test_note_issues_reports_missing_fields_and_unreadable_start(
    tmp_path, error
) -> None:
    file_service = MagicMock()
    parser = MagicMock()
    audit = DailyAuditService(file_service, MagicMock(), parser, str(tmp_path), "md")
    audit.time_service.get_start_time.side_effect = error
    audit.file_service.check_finalized_in_file.return_value = False
    audit.parser.parse.return_value = ParsedNote(time_spent=" \t", summary=[" ", ""])

    assert audit.note_issues("day.md") == [
        "missing start time",
        "missing end time",
        "missing time spent",
        "missing summary",
    ]
    file_service.get_lines.assert_called_once_with("day.md")
    parser.parse.assert_called_once_with("day.md")


def test_note_issues_accepts_completed_note_and_absent_parse(tmp_path) -> None:
    time_service = MagicMock()
    audit = DailyAuditService(
        MagicMock(), time_service, MagicMock(), str(tmp_path), "md"
    )
    audit.file_service.get_lines.return_value = ["start"]
    audit.file_service.check_finalized_in_file.return_value = True
    audit.parser.parse.return_value = ParsedNote(time_spent="1h", summary=[" ", "Done"])

    assert audit.note_issues("day.md") == []
    time_service.get_start_time.assert_called_once_with(["start"])

    audit.parser.parse.return_value = None
    assert audit.note_issues("day.md") == []


def test_audit_daily_notes_sorts_and_filters_entries(tmp_path) -> None:
    audit = make_audit(tmp_path)
    assert audit.audit_daily_notes(2025) == []

    week_a = tmp_path / "2025" / "week01"
    week_b = tmp_path / "2025" / "week02"
    week_a.mkdir(parents=True)
    week_b.mkdir()
    (tmp_path / "2025" / "week00").touch()
    first = week_a / "2025-01-01-DailyNotes.md"
    second = week_b / "2025-01-08-DailyNotes.md"
    for path in (
        second,
        first,
        week_a / "2025-01-01-DailyNotes-Holidays.md",
        week_b / "notes.txt",
    ):
        path.touch()
    with patch.object(
        audit, "note_issues", side_effect=[["missing summary"], []]
    ) as issues:
        assert audit.audit_daily_notes(2025) == [
            ("2025-01-01", str(first), ["missing summary"]),
            ("2025-01-08", str(second), []),
        ]
    assert issues.call_args_list == [call(str(first)), call(str(second))]


def test_count_week_folders_ignores_files_and_other_directories(tmp_path) -> None:
    audit = make_audit(tmp_path)
    assert audit.count_week_folders(2025) == 0

    year = tmp_path / "2025"
    year.mkdir()
    (year / "week01").mkdir()
    (year / "week02").touch()
    (year / "archive").mkdir()
    assert audit.count_week_folders(2025) == 1


def test_audit_weekly_coverage_skips_future_invalid_and_excused_dates(tmp_path) -> None:
    audit = make_audit(tmp_path)
    assert audit.audit_weekly_coverage(2025) == []

    year = tmp_path / "2025"
    for week in ("week02", "week03", "week53", "weekbad"):
        (year / week).mkdir(parents=True)
    (year / "week04").touch()
    (year / "archive").mkdir()
    (year / "week02" / "2025-01-06-DailyNotes.md").touch()
    (year / "week02" / "2025-01-07-DailyNotes-Holidays.md").touch()

    with patch("taskjournal.services.daily_audit.date_t", wraps=date) as clock:
        clock.today.return_value = date(2025, 1, 8)
        assert audit.audit_weekly_coverage(2025) == [("week02", ["2025-01-08"])]


def test_previous_day_finds_first_existing_note_and_reports_only_issues(
    tmp_path,
) -> None:
    audit = make_audit(tmp_path)
    today = datetime(2025, 1, 20)
    get_path = lambda day: str(tmp_path / f"{day:%Y-%m-%d}-DailyNotes.md")
    (tmp_path / "2025-01-18-DailyNotes.md").touch()
    (tmp_path / "2025-01-17-DailyNotes.md").touch()

    with patch.object(audit, "note_issues", return_value=["missing summary"]) as issues:
        assert audit.get_previous_day_issues(today, get_path) == (
            "2025-01-18",
            get_path(datetime(2025, 1, 18)),
            ["missing summary"],
        )
    issues.assert_called_once_with(get_path(datetime(2025, 1, 18)))

    with patch.object(audit, "note_issues", return_value=[]):
        assert audit.get_previous_day_issues(today, get_path) is None


def test_previous_day_checks_fourteen_days_but_not_fifteen(tmp_path) -> None:
    audit = make_audit(tmp_path)
    today = datetime(2025, 1, 20)
    get_path = lambda day: str(tmp_path / f"{day:%Y-%m-%d}-DailyNotes.md")
    (tmp_path / "2025-01-05-DailyNotes.md").touch()
    with patch.object(audit, "note_issues") as issues:
        assert audit.get_previous_day_issues(today, get_path) is None
    issues.assert_not_called()

    (tmp_path / "2025-01-06-DailyNotes.md").touch()
    with patch.object(audit, "note_issues", return_value=["missing end time"]):
        assert audit.get_previous_day_issues(today, get_path) == (
            "2025-01-06",
            get_path(datetime(2025, 1, 6)),
            ["missing end time"],
        )


def test_warn_incomplete_week_notes_only_logs_existing_incomplete_weekdays(
    tmp_path,
) -> None:
    audit = make_audit(tmp_path)
    week = tmp_path / "week02"
    week.mkdir()
    monday = week / "2025-01-06-DailyNotes.md"
    wednesday = week / "2025-01-08-DailyNotes.md"
    saturday = week / "2025-01-11-DailyNotes.md"
    for path in (monday, wednesday, saturday):
        path.touch()
    audit.time_service.get_daily_notes_name.side_effect = (
        lambda day: f"{day:%Y-%m-%d}-DailyNotes.md"
    )

    with patch.object(
        audit, "note_issues", side_effect=[["missing summary", "missing end time"], []]
    ) as issues:
        with patch("taskjournal.services.daily_audit.logger") as mocked_logger:
            audit.warn_incomplete_week_notes(datetime(2025, 1, 8), str(week))
    assert issues.call_args_list == [call(str(monday)), call(str(wednesday))]
    assert mocked_logger.warning.call_args_list == [
        call("Week report generated with incomplete notes:"),
        call("  ⚠  2025-01-06: missing summary, missing end time"),
    ]

    with patch.object(audit, "note_issues", return_value=[]):
        with patch("taskjournal.services.daily_audit.logger") as mocked_logger:
            audit.warn_incomplete_week_notes(datetime(2025, 1, 8), str(week))
    mocked_logger.warning.assert_not_called()


def test_iter_daily_notes_filters_invalid_names_and_sorts(tmp_path) -> None:
    audit = make_audit(tmp_path)
    assert list(audit.iter_daily_notes(2025)) == []

    year = tmp_path / "2025"
    for week_name in ("week02", "week01"):
        (year / week_name).mkdir(parents=True)
    (year / "week00").touch()
    first = year / "week01" / "2025-01-02-DailyNotes.md"
    second = year / "week02" / "2025-01-07-DailyNotes.md"
    for path in (
        second,
        first,
        year / "week01" / "2025-02-30-DailyNotes.md",
        year / "week02" / "2025-01-08-DailyNotes-Holidays.md",
        year / "week02" / "2025-01-09-DailyNotes.txt",
    ):
        path.touch()
    assert list(audit.iter_daily_notes(2025)) == [
        (datetime(2025, 1, 2), str(first)),
        (datetime(2025, 1, 7), str(second)),
    ]


def test_iter_streak_dates_accepts_legacy_files_but_ignores_bad_dates(tmp_path) -> None:
    audit = make_audit(tmp_path)
    assert list(audit.iter_streak_dates()) == []

    archive = tmp_path / "archive"
    archive.mkdir()
    for path in (
        tmp_path / "2025-01-06-DailyNotes.md",
        archive / "2025-01-07-OldDailyNotes.txt",
        archive / "2025-02-30-DailyNotes.md",
        archive / "memo-2025-01-08-DailyNotes.md",
        archive / "2025-01-09-Notes.md",
    ):
        path.touch()
    assert set(audit.iter_streak_dates()) == {date(2025, 1, 6), date(2025, 1, 7)}
