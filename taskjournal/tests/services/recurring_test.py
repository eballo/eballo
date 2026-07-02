import json
from datetime import datetime
from pathlib import Path

from pytest import fixture, raises
from pytest_mock import MockerFixture

from taskjournal.services.recurring import RecurringTasksService


@fixture
def recurring_file(tmp_path: Path) -> str:
    return str(tmp_path / "recurring" / "recurring_tasks.json")


@fixture
def service(recurring_file: str) -> RecurringTasksService:
    return RecurringTasksService(file_path=recurring_file)


class TestRecurringTasksService:

    def test_name(self, service: RecurringTasksService) -> None:
        assert service.name == "RecurringTasksService"

    def test_health_check_returns_ok(self, service: RecurringTasksService) -> None:
        from taskjournal.services.base import ServiceStatus
        result = service.health_check()
        assert result.status == ServiceStatus.OK

    def test_load_returns_empty_when_file_missing(self, service: RecurringTasksService) -> None:
        assert service._load() == []

    def test_load_returns_tasks_when_file_exists(self, service: RecurringTasksService, recurring_file: str) -> None:
        tasks = [{"description": "standup", "days": "every"}]
        Path(recurring_file).parent.mkdir(parents=True, exist_ok=True)
        Path(recurring_file).write_text(json.dumps(tasks))
        assert service._load() == tasks

    def test_load_returns_empty_on_invalid_json(self, service: RecurringTasksService, recurring_file: str) -> None:
        Path(recurring_file).parent.mkdir(parents=True, exist_ok=True)
        Path(recurring_file).write_text("not-valid-json")
        assert service._load() == []

    def test_load_returns_empty_when_data_is_not_list(self, service: RecurringTasksService, recurring_file: str) -> None:
        Path(recurring_file).parent.mkdir(parents=True, exist_ok=True)
        Path(recurring_file).write_text(json.dumps({"key": "value"}))
        assert service._load() == []

    def test_add_every_day_when_no_days_given(self, service: RecurringTasksService) -> None:
        service.add("standup")
        tasks = service._load()
        assert len(tasks) == 1
        assert tasks[0]["description"] == "standup"
        assert tasks[0]["days"] == "every"

    def test_add_specific_days(self, service: RecurringTasksService) -> None:
        service.add("sync", days=["monday", "wednesday"])
        tasks = service._load()
        assert tasks[0]["days"] == ["monday", "wednesday"]

    def test_add_updates_existing_task_days(self, service: RecurringTasksService) -> None:
        service.add("standup", days=["monday"])
        service.add("standup", days=["tuesday", "thursday"])
        tasks = service._load()
        assert len(tasks) == 1
        assert tasks[0]["days"] == ["tuesday", "thursday"]

    def test_add_raises_on_unknown_day(self, service: RecurringTasksService) -> None:
        with raises(ValueError, match="Unknown day"):
            service.add("standup", days=["funday"])

    def test_remove_returns_true_when_task_found(self, service: RecurringTasksService) -> None:
        service.add("standup")
        result = service.remove("standup")
        assert result is True
        assert service._load() == []

    def test_remove_returns_false_when_task_not_found(self, service: RecurringTasksService) -> None:
        result = service.remove("nonexistent")
        assert result is False

    def test_list_all_returns_all_tasks(self, service: RecurringTasksService) -> None:
        service.add("standup")
        service.add("sync", days=["friday"])
        result = service.list_all()
        assert len(result) == 2

    def test_get_for_day_returns_every_day_tasks(self, service: RecurringTasksService) -> None:
        service.add("standup")
        monday = datetime(2025, 1, 20)
        assert "standup" in service.get_for_day(monday)

    def test_get_for_day_returns_day_specific_task(self, service: RecurringTasksService) -> None:
        service.add("weekly sync", days=["friday"])
        friday = datetime(2025, 1, 24)
        monday = datetime(2025, 1, 20)
        assert "weekly sync" in service.get_for_day(friday)
        assert "weekly sync" not in service.get_for_day(monday)

    def test_get_for_day_ignores_empty_description(self, service: RecurringTasksService, recurring_file: str) -> None:
        tasks = [{"description": "", "days": "every"}, {"description": "standup", "days": "every"}]
        Path(recurring_file).parent.mkdir(parents=True, exist_ok=True)
        Path(recurring_file).write_text(json.dumps(tasks))
        monday = datetime(2025, 1, 20)
        result = service.get_for_day(monday)
        assert result == ["standup"]

    def test_add_monthly_stores_monthly_first_workday(self, service: RecurringTasksService) -> None:
        service.add("Deel report", monthly=True)
        tasks = service._load()
        assert tasks[0]["days"] == "monthly_first_workday"

    def test_add_monthly_and_every_are_mutually_exclusive_via_monthly_flag(self, service: RecurringTasksService) -> None:
        service.add("Deel report", monthly=True)
        service.add("standup")
        tasks = service._load()
        assert len(tasks) == 2
        assert tasks[0]["days"] == "monthly_first_workday"
        assert tasks[1]["days"] == "every"

    def test_get_for_day_returns_monthly_on_first_workday(self, service: RecurringTasksService) -> None:
        service.add("Deel report", monthly=True)
        # 2025-07-01 is a Tuesday — first workday of July
        first_workday = datetime(2025, 7, 1)
        assert "Deel report" in service.get_for_day(first_workday)

    def test_get_for_day_skips_monthly_on_other_days(self, service: RecurringTasksService) -> None:
        service.add("Deel report", monthly=True)
        # 2025-07-02 is a Wednesday — not the first workday
        second_day = datetime(2025, 7, 2)
        assert "Deel report" not in service.get_for_day(second_day)

    def test_get_for_day_monthly_skips_weekend_start(self, service: RecurringTasksService) -> None:
        service.add("Deel report", monthly=True)
        # 2025-06-01 is a Sunday — first workday is Monday 2025-06-02
        sunday_first = datetime(2025, 6, 1)
        monday_first_workday = datetime(2025, 6, 2)
        assert "Deel report" not in service.get_for_day(sunday_first)
        assert "Deel report" in service.get_for_day(monday_first_workday)
