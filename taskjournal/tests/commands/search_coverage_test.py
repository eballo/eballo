from builtins import open as builtin_open
from datetime import datetime
from pathlib import Path

from pytest import fixture, mark
from pytest_mock import MockerFixture

from taskjournal.commands.search import SearchCommands


@fixture
def notes_dir(tmp_path: Path, mocker: MockerFixture) -> Path:
    mocker.patch("taskjournal.commands.search.BASE_DIR", tmp_path)
    mocker.patch("taskjournal.config.TEMPLATE_FORMAT", "md")
    return tmp_path


class TestSearchCommands:
    def test_search_notes__sorts_recursive_matches_and_treats_query_literally(
        self, notes_dir: Path
    ) -> None:
        later = notes_dir / "b"
        earlier = notes_dir / "a"
        later.mkdir()
        earlier.mkdir()
        (later / "2025-01-03-DailyNotes.md").write_text("A.B later\n")
        first = earlier / "2025-01-01-DailyNotes.md"
        first.write_text("not axb\nfirst a.b  \nA.B again\n", encoding="utf-8")
        second = earlier / "2025-01-02-week-summary.md"
        second.write_text("a.b in summary\n", encoding="utf-8")
        (earlier / "ignored.rst").write_text("a.b\n", encoding="utf-8")
        (earlier / "ignored.MD").write_text("a.b\n", encoding="utf-8")

        result = SearchCommands().search_notes("a.b")

        assert result == [
            (str(first), 2, "first a.b"),
            (str(first), 3, "A.B again"),
            (str(second), 1, "a.b in summary"),
            (str(later / "2025-01-03-DailyNotes.md"), 1, "A.B later"),
        ]

    @mark.parametrize(
        ("note_type", "expected_names"),
        [
            ("daily", ["2025-01-01-DailyNotes.md"]),
            ("week", ["2025-01-02-week-summary.md"]),
            (
                None,
                ["2025-01-01-DailyNotes.md", "2025-01-02-week-summary.md", "other.md"],
            ),
            (
                "other",
                ["2025-01-01-DailyNotes.md", "2025-01-02-week-summary.md", "other.md"],
            ),
        ],
    )
    def test_search_notes__filters_note_type(
        self, notes_dir: Path, note_type: str | None, expected_names: list[str]
    ) -> None:
        for name in (
            "2025-01-01-DailyNotes.md",
            "2025-01-02-week-summary.md",
            "other.md",
        ):
            (notes_dir / name).write_text("needle\n", encoding="utf-8")

        result = SearchCommands().search_notes("needle", note_type=note_type)

        assert [Path(path).name for path, _, _ in result] == expected_names

    @mark.parametrize(
        ("from_date", "to_date", "expected_names"),
        [
            (
                datetime(2025, 1, 2),
                None,
                ["2025-01-02-DailyNotes.md", "2025-01-03-DailyNotes.md"],
            ),
            (
                None,
                datetime(2025, 1, 2),
                ["2025-01-01-DailyNotes.md", "2025-01-02-DailyNotes.md"],
            ),
            (
                datetime(2025, 1, 2),
                datetime(2025, 1, 2),
                ["2025-01-02-DailyNotes.md"],
            ),
        ],
    )
    def test_search_notes__filters_dates_inclusively(
        self,
        notes_dir: Path,
        from_date: datetime | None,
        to_date: datetime | None,
        expected_names: list[str],
    ) -> None:
        for day in (1, 2, 3):
            (notes_dir / f"2025-01-{day:02d}-DailyNotes.md").write_text("needle\n")

        result = SearchCommands().search_notes("needle", from_date, to_date)

        assert [Path(path).name for path, _, _ in result] == expected_names

    def test_search_notes__keeps_undated_and_invalid_date_files_with_date_filter(
        self, notes_dir: Path
    ) -> None:
        for name in (
            "notes.md",
            "2025-02-30-DailyNotes.md",
            "2025-01-01-DailyNotes.md",
        ):
            (notes_dir / name).write_text("needle\n")

        result = SearchCommands().search_notes(
            "needle", from_date=datetime(2025, 2, 1), to_date=datetime(2025, 2, 28)
        )

        assert [Path(path).name for path, _, _ in result] == [
            "2025-02-30-DailyNotes.md",
            "notes.md",
        ]

    def test_search_notes__skips_unreadable_file_and_continues(
        self, notes_dir: Path, mocker: MockerFixture
    ) -> None:
        unreadable = notes_dir / "2025-01-01-DailyNotes.md"
        unreadable.write_text("needle\n")
        readable = notes_dir / "2025-01-02-DailyNotes.md"
        readable.write_text("needle\n")

        def open_with_error(path: str, *, encoding: str):
            if path == str(unreadable):
                raise OSError("permission denied")
            return builtin_open(path, encoding=encoding)

        mocker.patch(
            "taskjournal.commands.search.open", create=True, side_effect=open_with_error
        )

        assert SearchCommands().search_notes("needle") == [(str(readable), 1, "needle")]

    def test_search_notes__finds_both_extensions(
        self, notes_dir: Path, mocker: MockerFixture
    ) -> None:
        mocker.patch("taskjournal.config.TEMPLATE_FORMAT", "txt")
        matching = notes_dir / "notes.txt"
        matching.write_text("needle\n")
        markdown = notes_dir / "notes.md"
        markdown.write_text("needle\n")

        assert SearchCommands().search_notes("needle") == [
            (str(markdown), 1, "needle"),
            (str(matching), 1, "needle"),
        ]
