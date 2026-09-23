from datetime import date, datetime
from unittest.mock import MagicMock

from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Status, Task
from taskjournal.services.daily_statistics import DailyStatisticsService


def _statistics(
    notes: list[tuple[datetime, str]], parsed: dict[str, ParsedNote | None]
) -> DailyStatisticsService:
    parser = MagicMock()
    parser.parse.side_effect = parsed.get
    audit = MagicMock()
    audit.iter_daily_notes.side_effect = lambda year: iter(notes)
    return DailyStatisticsService(parser, audit)


def test_completion_ignores_missing_and_empty_notes() -> None:
    days = [(datetime(2025, 1, d), str(d)) for d in (6, 7, 8)]
    stats = _statistics(
        days,
        {
            "6": None,
            "7": ParsedNote(),
            "8": ParsedNote(
                planned_tasks=[
                    Task(id="1", description="Done", status=Status.DONE),
                    Task(id="2", description="Pending"),
                ]
            ),
        },
    )

    assert stats.get_completion_stats(2025) == [("2025-01-08", 1, 2)]


def test_workload_sums_weeks_and_ignores_missing_or_malformed_times() -> None:
    days = [(datetime(2025, 1, d), str(d)) for d in (6, 7, 8, 13, 14)]
    stats = _statistics(
        days,
        {
            "6": ParsedNote(time_spent="01:30"),
            "7": ParsedNote(time_spent="worked 02:15 hours"),
            "8": ParsedNote(time_spent="unknown"),
            "13": None,
            "14": ParsedNote(time_spent="00:45"),
        },
    )

    assert stats.get_workload_stats(2025) == [("W02", 13500), ("W03", 2700)]


def test_patterns_track_carry_over_and_ignore_bad_start_times() -> None:
    days = [(datetime(2025, 1, d), str(d)) for d in (6, 7, 8, 11)]
    stats = _statistics(
        days,
        {
            "6": ParsedNote(
                start_time="09:00",
                planned_tasks=[
                    Task(id="1", description="Carry", status=Status.TODO),
                    Task(id="2", description="Finished", status=Status.DONE),
                ],
            ),
            "7": ParsedNote(
                start_time="10:30",
                planned_tasks=[
                    Task(id="3", description="Carry", status=Status.DONE),
                    Task(id="4", description="Blocked", status=Status.BLOCKED),
                ],
            ),
            "8": None,
            "11": ParsedNote(
                start_time="invalid",
                planned_tasks=[
                    Task(id="5", description="Blocked", status=Status.IN_PROGRESS),
                ],
            ),
        },
    )

    assert stats.get_pattern_stats(2025) == {
        "best_day": "Monday",
        "best_hour": 9,
        "avg_done_per_day": 0.7,
        "carry_over_rate": 67,
        "avg_by_day": {"Monday": 1.0, "Tuesday": 1.0},
    }


def test_patterns_without_valid_notes_have_no_best_day_or_hour() -> None:
    stats = _statistics([(datetime(2025, 1, 6), "missing")], {"missing": None})

    assert stats.get_pattern_stats(2025) == {
        "best_day": None,
        "best_hour": None,
        "avg_done_per_day": 0,
        "carry_over_rate": 0,
        "avg_by_day": {},
    }


def test_tags_count_repeated_tags_only_on_first_tags_line(tmp_path) -> None:
    first = tmp_path / "first.md"
    first.write_text("Title\nTags:  python, docs, , python\nTags: ignored\n")
    second = tmp_path / "second.md"
    second.write_text("No tags\nTags: docs, qa\n")
    stats = _statistics(
        [
            (datetime(2025, 1, 6), str(first)),
            (datetime(2025, 1, 7), str(second)),
        ],
        {},
    )

    assert stats.get_tags_stats(2025) == [("python", 2), ("docs", 2), ("qa", 1)]


def test_streak_without_notes_has_zero_totals() -> None:
    audit = MagicMock()
    audit.iter_streak_dates.return_value = iter(())

    assert DailyStatisticsService(MagicMock(), audit).get_streak_stats(
        datetime(2025, 1, 7)
    ) == {
        "current": 0,
        "longest": 0,
        "longest_start": None,
        "longest_end": None,
        "total": 0,
    }


def test_streak_skips_weekend_and_holiday_and_retains_longest_run(mocker) -> None:
    holiday = mocker.patch("taskjournal.services.daily_statistics.HolidayService")
    holiday.return_value.is_holiday.side_effect = lambda d: (
        "holiday" if d.date() == date(2025, 1, 6) else None
    )
    audit = MagicMock()
    audit.iter_streak_dates.return_value = iter(
        [
            date(2025, 1, 3),
            date(2025, 1, 7),
            date(2025, 1, 8),
            date(2025, 1, 10),
        ]
    )

    assert DailyStatisticsService(MagicMock(), audit).get_streak_stats(
        datetime(2025, 1, 11)
    ) == {
        "current": 1,
        "longest": 3,
        "longest_start": date(2025, 1, 3),
        "longest_end": date(2025, 1, 8),
        "total": 4,
    }
    assert holiday.call_count == 1


def test_streak_current_continues_back_from_non_working_today(mocker) -> None:
    mocker.patch(
        "taskjournal.services.daily_statistics.HolidayService"
    ).return_value.is_holiday.return_value = None
    audit = MagicMock()
    audit.iter_streak_dates.return_value = iter([date(2025, 1, 9), date(2025, 1, 10)])

    result = DailyStatisticsService(MagicMock(), audit).get_streak_stats(
        datetime(2025, 1, 12)
    )

    assert result["current"] == 2
    assert result["longest"] == 2
