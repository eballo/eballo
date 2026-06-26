from collections.abc import Callable
from datetime import datetime
from unittest.mock import MagicMock

from freezegun import freeze_time
from rich.text import Text
from typer.testing import Result


class TestSearch:

    @freeze_time("2026-03-01 10:00:00")
    def test_search_no_results_prints_no_matches(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.search_notes.return_value = []

        result = invoke_cli(["search", "--query", "nothing"])

        assert result.exit_code == 0
        assert "No matches found" in result.output

    @freeze_time("2026-03-01 10:00:00")
    def test_search_with_results_groups_by_file(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.search_notes.return_value = [
            ("/base/week01/2026-01-05-DailyNotes.md", 3, "fix the bug"),
            ("/base/week01/2026-01-05-DailyNotes.md", 7, "another fix"),
            ("/base/week02/2026-01-12-DailyNotes.md", 2, "fix later"),
        ]

        result = invoke_cli(["search", "--query", "fix"])

        assert result.exit_code == 0
        assert "week01/2026-01-05-DailyNotes.md" in result.output
        assert "week02/2026-01-12-DailyNotes.md" in result.output
        assert "3 matches" in result.output

    @freeze_time("2026-03-01 10:00:00")
    def test_search_passes_filters_to_manager(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.search_notes.return_value = []

        invoke_cli([
            "search",
            "--query", "todo",
            "--from", "2026-01-01",
            "--to", "2026-01-31",
            "--type", "daily",
        ])

        cli_manager.search_notes.assert_called_once_with(
            "todo",
            datetime(2026, 1, 1),
            datetime(2026, 1, 31),
            "daily",
        )

    @freeze_time("2026-03-01 10:00:00")
    def test_search_singular_match_label(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        cli_manager.search_notes.return_value = [
            ("/base/week01/2026-01-05-DailyNotes.md", 1, "found it"),
        ]

        result = invoke_cli(["search", "--query", "found"])

        assert "1 match in 1 file" in result.output


class TestSearchHelpers:

    def test_short_path_returns_folder_slash_filename(self) -> None:
        from taskjournal.cli.commands.search import _short_path

        result = _short_path("/base/2026/week01/2026-01-05-DailyNotes.md")

        assert result == "week01/2026-01-05-DailyNotes.md"

    def test_highlight_wraps_match_in_bold_yellow(self) -> None:
        from taskjournal.cli.commands.search import _highlight

        result = _highlight("Fix the BUG now", "bug")

        assert isinstance(result, Text)
        plain = result.plain
        assert "Fix the BUG now" == plain

    def test_highlight_no_match_returns_plain(self) -> None:
        from taskjournal.cli.commands.search import _highlight

        result = _highlight("nothing here", "xyz")

        assert result.plain == "nothing here"

    def test_highlight_multiple_occurrences(self) -> None:
        from taskjournal.cli.commands.search import _highlight

        result = _highlight("fix this fix that", "fix")

        assert result.plain == "fix this fix that"
        spans = [s for s in result._spans if "bold" in str(s.style)]
        assert len(spans) == 2
