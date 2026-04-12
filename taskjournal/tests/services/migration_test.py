from typing import Any

from pytest_mock import MockerFixture

from datetime import datetime

from taskjournal.models.task import Status, Task
from taskjournal.services.migration import MigrationService


def _sample_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "sprint_name": "",
        "date": None,
        "start_time": None,
        "end_time": None,
        "time_spent": "",
        "work_from": "",
        "planned_tasks": [],
        "code_review_tasks": [],
        "notes": ["note 1", "note 2"],
        "summary": ["summary 1"],
        "firefighter": [],
    }
    data.update(overrides)
    return data


class TestMigration:

    def test_migration_info_logs_summary(
        self, migration_service: MigrationService, mocker: MockerFixture
    ) -> None:
        # given
        logger = mocker.patch("taskjournal.services.migration.logger")

        # when
        migration_service.migration_info()

        # then
        assert logger.info.call_count == 3

    def test_migrate_file_skips_non_txt_and_updates_stats(
        self,
        migration_service: MigrationService,
        mocker: MockerFixture,
    ) -> None:
        # given
        logger = mocker.patch("taskjournal.services.migration.logger")

        # when
        migration_service.migrate_file("daily.md")

        # then
        assert migration_service.statistics["migrated_files"] == 0
        assert migration_service.statistics["skipped_files"] == 1
        logger.warning.assert_called_once()

    def test_migrate_file_success_creates_md_file(
        self, migration_service: MigrationService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(
            migration_service.daily_parser_service, "parse", return_value=_sample_data()
        )
        mocker.patch.object(
            migration_service,
            "_extract_datetime_object",
            return_value=datetime(2025, 1, 10, 9, 0, 0),
        )
        mocker.patch.object(
            migration_service, "_generate_md_content", return_value="rendered markdown"
        )
        mock_file = mocker.mock_open()
        mocker.patch("builtins.open", mock_file)

        # when
        migration_service.migrate_file("2025-01-10-DailyNotes.txt")

        # then
        assert migration_service.statistics["migrated_files"] == 1
        assert migration_service.statistics["skipped_files"] == 0
        mock_file.assert_called_once_with(
            "2025-01-10-DailyNotes.md", "w", encoding="utf-8"
        )
        mock_file().write.assert_called_once_with("rendered markdown")

    def test_migrate_file_logs_error_on_exception(
        self, migration_service: MigrationService, mocker: MockerFixture
    ) -> None:
        # given
        logger = mocker.patch("taskjournal.services.migration.logger")
        mocker.patch.object(
            migration_service.daily_parser_service,
            "parse",
            side_effect=RuntimeError("boom"),
        )

        # when
        migration_service.migrate_file("2025-01-10-DailyNotes.txt")

        # then
        assert migration_service.statistics["migrated_files"] == 0
        logger.error.assert_called_once()

    def test_extract_datetime_object_success_and_none(self) -> None:
        # when
        assert MigrationService._extract_datetime_object(
            "path/2025-01-10-DailyNotes.txt"
        ) == datetime(2025, 1, 10)
        # then
        assert MigrationService._extract_datetime_object("path/no-date.txt") is None

    def test_generate_md_content_uses_fallback_values(
        self, migration_service: MigrationService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(
            migration_service.task_manager, "get_work_from_location", return_value="Home"
        )
        mocker.patch(
            "taskjournal.services.file.FileService.load_template",
            return_value=(
                "Sprint={{ sprint_name }}|Date={{ date }}|Start={{ start_time }}|"
                "End={{ end_time }}|Spent={{ time_spent }}|WF={{ work_from }}|"
                "Tasks={{ tasks }}|CR={{ code_review_tasks }}|Notes={{ notes }}|"
                "Summary={{ summary }}|FF={{ firefighter }}|FFN={{ firefighter_notes }}"
            ),
        )
        mocker.patch.object(
            migration_service, "_calculate_time_spent", return_value="08:30"
        )
        mocker.patch.object(
            migration_service.task_formatter,
            "format_tasks",
            side_effect=["planned", "review"],
        )

        result = migration_service._generate_md_content(
            _sample_data(),
            datetime(2025, 1, 9, 9, 0, 0),
            # when
        )

        # then
        assert "Sprint=No active sprint" in result
        assert "Date=2025-01-09" in result
        assert "Start=09:00:00" in result
        assert "End=18:30:00" in result
        assert "Spent=08:30" in result
        assert "WF=Home" in result
        assert "Tasks=planned" in result
        assert "CR=review" in result
        assert "Notes=note 1\nnote 2" in result
        assert "Summary=summary 1" in result
        assert "FF=False" in result
        assert "FFN=" in result

    def test_generate_md_content_uses_provided_values(
        self, migration_service: MigrationService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(
            migration_service.task_manager, "get_work_from_location", return_value="Office"
        )
        mocker.patch(
            "taskjournal.services.file.FileService.load_template",
            return_value="End={{ end_time }}|Spent={{ time_spent }}|FF={{ firefighter }}|FFN={{ firefighter_notes }}",
        )
        mocker.patch.object(
            migration_service.task_formatter, "format_tasks", return_value=""
        )

        result = migration_service._generate_md_content(
            _sample_data(
                sprint_name="Sprint 12",
                date="2025-01-03",
                start_time="10:00:00",
                end_time="12:00:00",
                time_spent="02:00",
                firefighter=["incident 1", "incident 2"],
            ),
            datetime(2025, 1, 3, 10, 0, 0),
            # when
        )

        # then
        assert "End=12:00:00" in result
        assert "Spent=02:00" in result
        assert "FF=True" in result
        assert "FFN=incident 1\nincident 2" in result

    def test_get_end_time_for_regular_day_and_friday(self) -> None:
        # when
        assert (
            MigrationService._get_end_time(datetime(2025, 1, 9, 10, 0, 0)) == "18:30:00"
        )
        # then
        assert (
            MigrationService._get_end_time(datetime(2025, 1, 10, 10, 0, 0))
            == "14:00:00"
        )

    def test_format_md_task_for_all_statuses(self) -> None:
        # given
        done = Task(id="1", description="done", status=Status.DONE)
        blocked = Task(id="2", description="blocked", status=Status.BLOCKED)
        # when
        todo = Task(id="3", description="todo", status=Status.TODO)

        # then
        assert MigrationService._format_md_task(done) == " - [x] done"
        assert MigrationService._format_md_task(blocked) == " - [-] blocked"
        assert MigrationService._format_md_task(todo) == " - [ ] todo"

    def test_calculate_time_spent_valid_and_fallback(
        self, mocker: MockerFixture
    ) -> None:
        # when
        logger = mocker.patch("taskjournal.services.migration.logger")

        # then
        assert MigrationService._calculate_time_spent("09:00", "10:15") == "01:15"
        assert MigrationService._calculate_time_spent("09:00:00", "18:30:00") == "09:30"
        assert MigrationService._calculate_time_spent("not-a-time", "10:15") == "08:30"
        logger.warning.assert_called_once()
