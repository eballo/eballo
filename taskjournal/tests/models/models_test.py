from datetime import datetime

import pytest
from pydantic import ValidationError

from taskjournal.models.task import (
    Task,
    Status,
)


def test_task_creation_minimal():
    task = Task(id="1", description="Write tests", status=Status.NOT_FINISHED)
    assert task.id == "1"
    assert task.description == "Write tests"
    assert task.status == Status.NOT_FINISHED
    assert task.start_time is None
    assert task.end_time is None


def test_task_creation_with_times():
    now = datetime.now()
    later = now.replace(hour=(now.hour + 1) % 24)
    task = Task(
        id="2",
        description="Code review",
        status=Status.NOT_FINISHED,
        start_time=now,
        end_time=later,
    )

    assert task.start_time == now
    assert task.end_time == later


def test_task_invalid_datetime():
    with pytest.raises(ValidationError):
        Task(
            id="3",
            description="Invalid datetime",
            status=Status.NOT_FINISHED,
            start_time="not-a-datetime",
        )


def test_task_missing_required_fields():
    with pytest.raises(ValidationError):
        Task(description="Missing ID", status=Status.NOT_FINISHED)

    with pytest.raises(ValidationError):
        Task(id="4", status=Status.DONE)
