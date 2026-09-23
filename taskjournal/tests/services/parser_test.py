from pytest import raises
from pytest_mock import MockerFixture

from taskjournal.container import AppContainer
from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Status
from taskjournal.services.parser import (
    DailyParserService,
    MarkdownParseStrategy,
    ParserService,
    PlainTextParseStrategy,
    TaskParseStrategy,
    get_parse_strategy,
)
from taskjournal.services.parsing import task_strategies


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

    def test_get_parse_strategy(self) -> None:
        assert isinstance(get_parse_strategy("md"), MarkdownParseStrategy)
        assert isinstance(get_parse_strategy(".md"), MarkdownParseStrategy)
        assert isinstance(get_parse_strategy("txt"), PlainTextParseStrategy)
        assert isinstance(get_parse_strategy(".txt"), PlainTextParseStrategy)
        assert isinstance(get_parse_strategy("other"), MarkdownParseStrategy)

    def test_strategy_exports_and_container_parser(self) -> None:
        assert TaskParseStrategy is task_strategies.TaskParseStrategy
        assert MarkdownParseStrategy is task_strategies.MarkdownParseStrategy
        assert PlainTextParseStrategy is task_strategies.PlainTextParseStrategy

        container = AppContainer()
        parser = container.daily_parser()
        assert container.task_manager().parser is parser
        assert isinstance(parser.get_strategy(".md"), task_strategies.MarkdownParseStrategy)
        assert isinstance(parser.get_strategy(".txt"), task_strategies.PlainTextParseStrategy)

    def test_markdown_parse_strategy(self) -> None:
        strategy = MarkdownParseStrategy()
        assert strategy.task_regex is not None
        assert strategy.parse_task("invalid line") is None

        task = strategy.parse_task(" - [x] [BE-10](https://jira/10)[🐙](https://gh/10)Fix bug")
        assert task is not None
        assert task.key == "BE-10"
        assert task.link == "https://jira/10"
        assert task.github == "https://gh/10"
        assert task.description == "Fix bug"
        assert task.status == Status.DONE

    def test_plain_text_parse_strategy(self) -> None:
        strategy = PlainTextParseStrategy()
        assert strategy.task_regex is not None
        assert strategy.parse_task("invalid line") is None

        task = strategy.parse_task("[>] [FE-20] Build UI 🔗 https://jira/20 🐙 https://gh/20")
        assert task is not None
        assert task.key == "FE-20"
        assert task.link == "https://jira/20"
        assert task.github == "https://gh/20"
        assert task.description == "Build UI"
        assert task.status == Status.IN_PROGRESS

    def test_daily_parser_custom_strategy_injection(self) -> None:
        class CustomParseStrategy(TaskParseStrategy):
            @property
            def task_regex(self):
                from re import compile
                return compile(r"^\*\s*\[([ xX])\]\s*(.*)")

            def extract_metadata(self, remainder: str):
                return None, None, None, remainder

        custom_parser = DailyParserService(strategies={".custom": CustomParseStrategy()})
        note = ParsedNote()
        custom_parser._parse_tasks("planned_tasks", note, "* [x] Custom task item", ".custom")
        assert len(note.planned_tasks) == 1
        assert note.planned_tasks[0].description == "Custom task item"
        assert note.planned_tasks[0].status == Status.DONE

    def test_daily_parser_legacy_properties_and_static_methods(self) -> None:
        parser = DailyParserService()
        assert parser.task_regex_txt is not None
        assert parser.task_regex_md is not None
        assert parser.get_strategy("md") is not None

        key, link, gh, desc = DailyParserService._extract_md_metadata("[BE-1](https://j)[🐙](https://g)desc")
        assert key == "BE-1"
        assert link == "https://j"
        assert gh == "https://g"
        assert desc == "desc"

        key, link, gh, desc = DailyParserService._extract_txt_metadata("[BE-1] desc 🔗 https://j 🐙 https://g")
        assert key == "BE-1"
        assert link == "https://j"
        assert gh == "https://g"
        assert desc == "desc"

    def test_daily_parser_parse_breaks_and_file_read(self, tmp_path) -> None:
        file_path = tmp_path / "2026-01-15.md"
        file_path.write_text("Date: 2026-01-15\nBreak: 12:30\nBreak: 15:45\n", encoding="utf-8")
        parser = DailyParserService()
        note = parser.parse(str(file_path))
        assert note is not None
        assert note.breaks == ["12:30", "15:45"]
