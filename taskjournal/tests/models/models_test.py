from datetime import datetime

from pydantic import ValidationError
from pytest import raises

from taskjournal.models.task import (
    Task,
    Status,
)


class TestModels:

    def test_task_creation_minimal(self) -> None:
        # when
        task = Task(id="1", description="Write tests", status=Status.TODO)
        # then
        assert task.id == "1"
        assert task.description == "Write tests"
        assert task.status == Status.TODO
        assert task.start_time is None
        assert task.end_time is None

    def test_task_creation_with_times(self) -> None:
        # given
        now = datetime.now()
        later = now.replace(hour=(now.hour + 1) % 24)
        task = Task(
            id="2",
            description="Code review",
            status=Status.TODO,
            start_time=now,
            end_time=later,
            # when
        )

        # then
        assert task.start_time == now
        assert task.end_time == later

    def test_task_invalid_datetime(self) -> None:
        # when
        with raises(ValidationError):
            Task(
                id="3",
                description="Invalid datetime",
                status=Status.TODO,
                start_time="not-a-datetime",
                # then
            )

    def test_task_missing_required_fields(self) -> None:
        # when
        with raises(ValidationError):
            Task(description="Missing ID", status=Status.TODO)

        # then
        with raises(ValidationError):
            Task(id="4", status=Status.DONE)
