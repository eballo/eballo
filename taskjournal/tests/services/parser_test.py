from pytest import raises
from pytest_mock import MockerFixture

from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Status
from taskjournal.services.parser import ParserService, DailyParserService


class TestParser:

    def test_parser_service_base_class_raises(self) -> None:
        # given
        content = "content"

        # when
        with raises(NotImplementedError):
            ParserService().parse(content)

    def test_daily_parser_parse_logs_error_on_failure(
        self, daily_parser_service: DailyParserService, mocker: MockerFixture
    ) -> None:
        # given
        logger = mocker.patch("taskjournal.services.parser.logger")
        mocker.patch.object(
            daily_parser_service, "_get_lines", side_effect=OSError("boom")
        )

        # when
        result = daily_parser_service.parse("missing.md")

        # then
        assert result is None
        logger.error.assert_called_once()

    def test_daily_parser_parse_content_txt_sections_and_metadata(
        self, daily_parser_service: DailyParserService
    ) -> None:
        # given
        lines = [
            "Sprint: Sprint 42\n",
            "Date: 2026-01-15\n",
            "Start Time: 09:00:00\n",
            "End Time: 18:00:00\n",
            "Time Spent: 08:00\n",
            "Work from: Home\n",
            "## Planned Tasks\n",
            "[ ] Task TODO\n",
            "[x] Task DONE\n",
            "[-] Task BLOCKED\n",
            "## Code Review Tasks\n",
            "[ ] CR TODO\n",
            "## Notes\n",
            "\n",
            "Note line 1\n",
            "\n",
            "## Summary\n",
            "Accomplished today\n",
            "## Firefighter\n",
            "Incident one\n",
        ]

        # when
        data = daily_parser_service._parse_content(lines, ".txt")

        # then
        assert isinstance(data, ParsedNote)
        assert data.sprint_name == "Sprint 42"
        assert data.date == "2026-01-15"
        assert data.start_time == "09:00:00"
        assert data.end_time == "18:00:00"
        assert data.time_spent == "08:00"
        assert data.work_from == "Home"
        assert [t.status for t in data.planned_tasks] == [
            Status.TODO,
            Status.DONE,
            Status.BLOCKED,
        ]
        assert data.code_review_tasks[0].description == "CR TODO"
        assert data.notes == ["Note line 1", ""]
        assert data.summary == ["Accomplished today"]
        assert data.firefighter == ["Incident one"]

    def test_daily_parser_parse_content_md_tasks_and_finalized(
        self, daily_parser_service: DailyParserService
    ) -> None:
        # given
        lines = [
            "Finalized: 17:30:00\n",
            "Total Time Spent: 08:30\n",
            "Tasks:\n",
            " - [x] md done\n",
            " - [-] md blocked\n",
        ]

        # when
        data = daily_parser_service._parse_content(lines, ".md")

        # then
        assert data.end_time == "17:30:00"
        assert data.time_spent == "08:30"
        assert data.planned_tasks[0].status == Status.DONE
        assert data.planned_tasks[1].status == Status.BLOCKED

    def test_daily_parser_parse_tasks_no_match_keeps_section_empty(
        self, daily_parser_service: DailyParserService
    ) -> None:
        # given
        note = ParsedNote()

        daily_parser_service._parse_tasks("planned_tasks", note, "not a task", ".txt")
        # when
        daily_parser_service._parse_tasks(
            "code_review_tasks", note, "not a task", ".md"
        )

        # then
        assert note.planned_tasks == []
        assert note.code_review_tasks == []

    def test_daily_parser_parse_tasks_txt_recovers_key_link_github(
        self, daily_parser_service: DailyParserService
    ) -> None:
        # given: a line as rendered by TaskFormatter in txt mode
        note = ParsedNote()
        line = (
            "[x] [BE-1] Implement feature - Enric (Done) "
            "🔗 https://jira/task/BE-1 🐙 https://github/pr/123"
        )

        # when
        daily_parser_service._parse_tasks("planned_tasks", note, line, ".txt")

        # then
        task = note.planned_tasks[0]
        assert task.key == "BE-1"
        assert task.link == "https://jira/task/BE-1"
        assert task.github == "https://github/pr/123"
        assert task.status == Status.DONE
        assert task.description == "Implement feature - Enric (Done)"

    def test_daily_parser_parse_tasks_txt_round_trips_through_formatter(
        self, daily_parser_service: DailyParserService
    ) -> None:
        # given
        from taskjournal.models.task import Task
        from taskjournal.repositories.task_formatter import TaskFormatter

        original = Task(
            id="1",
            key="BE-42",
            description="Ship it",
            status=Status.TODO,
            link="https://jira/BE-42",
            github="https://github/pr/9",
        )
        rendered = TaskFormatter(template_format="txt").format_task(
            original, with_name=False, with_status=False
        )
        note = ParsedNote()

        # when
        daily_parser_service._parse_tasks("planned_tasks", note, rendered, ".txt")

        # then
        parsed = note.planned_tasks[0]
        assert (parsed.key, parsed.link, parsed.github) == (
            original.key,
            original.link,
            original.github,
        )
        assert parsed.description == "Ship it"

    def test_daily_parser_parse_tasks_txt_reads_legacy_markdown_links(
        self, daily_parser_service: DailyParserService
    ) -> None:
        # given: a .txt note written before the format change
        note = ParsedNote()
        line = "[ ] [BE-7](https://jira/BE-7)[🐙](https://github/pr/7)Legacy task"

        # when
        daily_parser_service._parse_tasks("planned_tasks", note, line, ".txt")

        # then
        task = note.planned_tasks[0]
        assert task.key == "BE-7"
        assert task.link == "https://jira/BE-7"
        assert task.github == "https://github/pr/7"

    def test_daily_parser_metadata_line_without_match_is_ignored(
        self, daily_parser_service: DailyParserService
    ) -> None:
        # given
        lines = ["Unknown metadata: value\n", "## Planned Tasks\n", "[ ] todo\n"]

        # when
        data = daily_parser_service._parse_content(lines, ".txt")

        # then
        assert data.sprint_name == ""
        assert len(data.planned_tasks) == 1

    def test_daily_parser_parse_work_from_with_emojis_and_markdown(
        self, daily_parser_service: DailyParserService
    ) -> None:
        # given
        lines = [
            "**Work from:** 🏠 Home\n",
            "**Work from:** 🏢 Office\n",
            "Work from: 🏠 Home\n",
            "Work from: Office\n",
        ]

        # when & then
        # 1. Markdown with bold and emoji
        data = daily_parser_service._parse_content([lines[0]], ".md")
        assert data.work_from == "🏠 Home"

        # 2. Markdown with bold and office emoji
        data = daily_parser_service._parse_content([lines[1]], ".md")
        assert data.work_from == "🏢 Office"

        # 3. Plain text with emoji
        data = daily_parser_service._parse_content([lines[2]], ".txt")
        assert data.work_from == "🏠 Home"

        # 4. Plain text standard
        data = daily_parser_service._parse_content([lines[3]], ".txt")
        assert data.work_from == "Office"
