from datetime import datetime
from pathlib import Path

from pytest import fixture, mark
from pytest_mock import MockerFixture

from taskjournal.commands.search import SearchCommands


@fixture
def notes_dir(tmp_path: Path, mocker: MockerFixture) -> Path:
    mocker.patch("taskjournal.commands.search.BASE_DIR", tmp_path)
    return tmp_path


@mark.parametrize("template_format", ["md", "txt"])
def test_search_notes__finds_both_formats_once(
    notes_dir: Path, mocker: MockerFixture, template_format: str
) -> None:
    mocker.patch("taskjournal.config.TEMPLATE_FORMAT", template_format)
    markdown = notes_dir / "2025-01-02-DailyNotes.md"
    text = notes_dir / "2025-01-02-DailyNotes.txt"
    markdown.write_text("needle\n", encoding="utf-8")
    text.write_text("needle\n", encoding="utf-8")
    (notes_dir / "2025-01-02-DailyNotes.rst").write_text("needle\n", encoding="utf-8")

    assert SearchCommands().search_notes("needle") == [
        (str(markdown), 1, "needle"),
        (str(text), 1, "needle"),
    ]


@mark.parametrize("template_format", ["md", "txt"])
@mark.parametrize("note_type", ["daily", "week"])
def test_search_notes__filters_mixed_formats_by_date_and_type(
    notes_dir: Path, mocker: MockerFixture, template_format: str, note_type: str
) -> None:
    mocker.patch("taskjournal.config.TEMPLATE_FORMAT", template_format)
    expected = []
    for day in (1, 2, 3):
        for kind in ("DailyNotes", "week-summary"):
            for extension in ("md", "txt"):
                path = notes_dir / f"2025-01-{day:02d}-{kind}.{extension}"
                path.write_text("needle\n", encoding="utf-8")
                if day == 2 and kind == (
                    "DailyNotes" if note_type == "daily" else "week-summary"
                ):
                    expected.append((str(path), 1, "needle"))

    assert (
        SearchCommands().search_notes(
            "needle",
            from_date=datetime(2025, 1, 2),
            to_date=datetime(2025, 1, 2),
            note_type=note_type,
        )
        == expected
    )
