from typing import Any

from pytest_mock import MockerFixture

from pytest import mark

from taskjournal.models.parsed_note import ParsedNote
from taskjournal.models.task import Status, Task, Epic
from taskjournal.services.task_manager import TaskManager


class TestTaskManager:

    def test_get_tasks_from_daily_notes(self, mocker: MockerFixture) -> None:
        # given
        mocker.patch("taskjournal.parser.file_parser.TEMPLATE_FORMAT", "txt")
        mock_file = mocker.mock_open(
            read_data="## Planned Tasks\n[x] Done Task\n[ ] Pending Task\n[ ] Another Pending\n"
        )
        mocker.patch("builtins.open", mock_file)
        task_manager = TaskManager(
            parser=mocker.MagicMock(wraps=_real_parser()),
            wifi_service=mocker.MagicMock(),
        )
        # Use a real parser that reads the mocked file
        from taskjournal.services.parser import DailyParserService
        task_manager = TaskManager(
            parser=DailyParserService(),
            wifi_service=mocker.MagicMock(),
        )

        # when
        tasks = task_manager.get_tasks_from_daily_notes("fake_path.txt")

        # then
        assert len(tasks) == 3
        assert tasks[0].description == "Done Task"
        assert tasks[0].status == Status.DONE
        assert tasks[1].description == "Pending Task"
        assert tasks[1].status == Status.TODO
        assert tasks[2].description == "Another Pending"
        assert tasks[2].status == Status.TODO

    def test_get_tasks_from_daily_notes_error(self, mocker: MockerFixture) -> None:
        # given
        mock_parser = mocker.MagicMock()
        mock_parser.parse.side_effect = OSError("boom")
        mock_logger = mocker.patch("taskjournal.services.task_manager.logger")
        task_manager = TaskManager(parser=mock_parser, wifi_service=mocker.MagicMock())

        # when
        tasks = task_manager.get_tasks_from_daily_notes("badfile.txt")

        # then
        assert tasks == []
        mock_logger.error.assert_called_once()
        assert "Error reading file badfile.txt" in mock_logger.error.call_args[0][0]

    @mark.parametrize(
        "weekday,isoweek,expected_task, expected_len",
        [
            ("Wednesday", 3, "Check refinement tasks", 6),
            ("Thursday", 4, "Get ready for the retro points", 6),  # even week
            ("Thursday", 3, None, 5),  # odd week
            ("Friday", 3, "Write down the summary of the week", 6),
            ("Monday", 3, "New relic alarms - report", 6),
        ],
    )
    def test_get_default_tasks_varies_by_day(
        self,
        mocker: MockerFixture,
        weekday: str,
        isoweek: int,
        expected_task: str | None,
        expected_len: int,
    ) -> None:
        # given
        mock_datetime = mocker.patch("taskjournal.services.task_manager.datetime")
        mock_datetime.now.return_value.strftime.return_value = weekday
        mock_datetime.now.return_value.isocalendar.return_value = (2025, isoweek, 1)

        # when
        tasks = TaskManager.get_default_tasks()

        # then
        assert len(tasks) == expected_len
        assert "Check emails" in tasks[0].description
        assert "Check Calendar" in tasks[1].description
        assert "Check Jira" in tasks[2].description
        assert "Check Slack" in tasks[3].description
        assert "Check the sprint tasks in code review" in tasks[4].description

        if expected_task:
            assert expected_task in tasks[5].description
        else:
            assert all(
                exp not in tasks
                for exp in [
                    "[ ] Check refinement tasks",
                    "[ ] Get ready for the retro points",
                    "[ ] Write down the summary of the week",
                ]
            )

    def test_get_previous_tasks_folder_not_exist(self, mocker: MockerFixture) -> None:
        # given
        mocker.patch("taskjournal.services.task_manager.exists", return_value=False)
        task_manager = TaskManager(parser=mocker.MagicMock(), wifi_service=mocker.MagicMock())
        # when
        result = task_manager.get_previous_pending_tasks("fake_folder", "current.txt")
        # then
        assert result == []

    def test_get_previous_tasks_no_txt_files(self, mocker: MockerFixture) -> None:
        # given
        mocker.patch("taskjournal.services.task_manager.exists", return_value=True)
        mocker.patch("taskjournal.services.task_manager.listdir", return_value=["current.txt", "image.png"])
        task_manager = TaskManager(parser=mocker.MagicMock(), wifi_service=mocker.MagicMock())
        # when
        result = task_manager.get_previous_pending_tasks("some_folder", "current.txt")
        # then
        assert result == []

    def test_get_previous_tasks_success(self, mocker: MockerFixture) -> None:
        # given
        mocker.patch("taskjournal.services.task_manager.TEMPLATE_FORMAT", "txt")
        mocker.patch("taskjournal.parser.file_parser.TEMPLATE_FORMAT", "txt")
        mocker.patch("taskjournal.services.task_manager.exists", return_value=True)
        mocker.patch(
            "taskjournal.services.task_manager.listdir", return_value=["2025-01-18-DailyNotes.txt", "current.txt"]
        )
        mock_file = mocker.mock_open(
            read_data="## Planned Tasks\n[ ] Task 1\n[x] Task 2\n[ ] Task 3\n"
        )
        mocker.patch("builtins.open", mock_file)
        from taskjournal.services.parser import DailyParserService
        task_manager = TaskManager(
            parser=DailyParserService(),
            wifi_service=mocker.MagicMock(),
        )
        # when
        result = task_manager.get_previous_pending_tasks("folder", "current.txt")
        # then
        assert len(result) == 2

    def test_create_task_generates_todo_with_uuid(self) -> None:
        # when
        task = TaskManager.create_task("Do a thing")
        # then
        assert task.description == "Do a thing"
        assert task.status == Status.TODO
        assert task.id

    def test_get_work_from_location_prefers_wifi(self, mocker: MockerFixture) -> None:
        # given — wifi returns a known network (Office)
        mock_wifi = mocker.MagicMock()
        mock_wifi.get_name.return_value = "TSH"  # OFFICE_WIFI value
        mock_wifi.office_wifi = "TSH"
        task_manager = TaskManager(parser=mocker.MagicMock(), wifi_service=mock_wifi)

        # when
        result = task_manager.get_work_from_location(mocker.MagicMock())

        # then
        assert result == "Office"

    def test_get_default_locations_home_and_office(self) -> None:
        assert TaskManager._get_default_locations(mocker_date("Tuesday")) == "Office"
        assert TaskManager._get_default_locations(mocker_date("Sunday")) == "Home"

    def test_get_location_from_wifi_for_known_and_unknown_network(
        self,
        mocker: MockerFixture,
    ) -> None:
        # given
        mock_wifi = mocker.MagicMock()
        mock_wifi.home_wifi = "CodePI"
        mock_wifi.office_wifi = "TSH"
        task_manager = TaskManager(parser=mocker.MagicMock(), wifi_service=mock_wifi)

        # when / then
        mock_wifi.get_name.return_value = "CodePI"
        assert task_manager._get_location_from_wifi() == "Home"

        mock_wifi.get_name.return_value = "TSH"
        assert task_manager._get_location_from_wifi() == "Office"

        mock_wifi.get_name.return_value = "Unknown"
        assert task_manager._get_location_from_wifi() is None

    def test_get_previous_pending_tasks_handles_parser_failure(
        self,
        mocker: MockerFixture,
    ) -> None:
        # given
        mocker.patch("taskjournal.services.task_manager.exists", return_value=True)
        mocker.patch(
            "taskjournal.services.task_manager.listdir", return_value=["2025-01-18-DailyNotes.md", "current.md"]
        )
        mock_parser = mocker.MagicMock()
        mock_parser.parse.side_effect = RuntimeError("boom")
        task_manager = TaskManager(parser=mock_parser, wifi_service=mocker.MagicMock())

        # when
        result = task_manager.get_previous_pending_tasks("folder", "current.md")

        # then
        assert result == []

    def test_get_pending_unique_and_epics_helpers(self) -> None:
        # given
        todo = Task(id="1", description="same", status=Status.TODO)
        done = Task(id="2", description="done", status=Status.DONE)
        todo_dup = Task(id="3", description="same", status=Status.TODO)
        epic = Epic(key="EPIC-1", summary="Epic")
        with_epic = Task(id="4", description="a", status=Status.TODO, epic=epic)
        with_same_epic = Task(id="5", description="b", status=Status.TODO, epic=epic)

        # when
        pending = TaskManager.get_pending_tasks(ParsedNote(planned_tasks=[todo, done]))
        # then
        assert pending == [todo]

        uniques = TaskManager.unique_tasks([todo, todo_dup, done])
        assert len(uniques) == 2

        # keyed Jira task replaces keyless default with same (case-insensitive) description
        default = Task(id="d1", description="Check Emails", status=Status.TODO)
        jira = Task(id="j1", description="check emails", status=Status.TODO, key="PROJ-42")
        merged = TaskManager.unique_tasks([default, jira])
        assert len(merged) == 1
        assert merged[0].key == "PROJ-42"

        epics = TaskManager.get_unique_epics([with_epic, with_same_epic, todo])
        assert len(epics) == 1
        assert epics[0].key == "EPIC-1"


def _real_parser():
    from taskjournal.services.parser import DailyParserService
    return DailyParserService()


def mocker_date(day_name: str) -> Any:
    class _D:
        @staticmethod
        def strftime(_fmt: str) -> str:
            return day_name

    return _D()
