from pytest_mock import MockerFixture

from taskjournal.models.task import Status, Task, User
from taskjournal.repositories.task_formatter import TaskFormatter


class TestTaskFormatter:

    def test_format_task_todo_with_optional_fields(self) -> None:
        # given
        formatter = TaskFormatter()
        task = Task(
            id="1",
            key="BE-1",
            description="Implement feature",
            status=Status.TODO,
            link="https://jira/task/BE-1",
            github="https://github/pr/123",
            assignee=User(name="Enric"),
        )

        # when
        result = formatter.format_task(task, with_name=True, with_status=True)

        # then
        assert result.startswith(" - [ ]")
        assert "[BE-1](https://jira/task/BE-1)" in result
        assert "[🐙](https://github/pr/123)" in result
        assert "Implement feature - Enric (To Do)" in result

    def test_format_task_done_and_blocked_statuses(self) -> None:
        # given
        formatter = TaskFormatter()
        done = Task(id="1", description="Done task", status=Status.DONE)
        blocked = Task(id="2", description="Blocked task", status=Status.BLOCKED)

        done_result = formatter.format_task(done, with_name=False, with_status=False)
        blocked_result = formatter.format_task(
            blocked,
            with_name=False,
            with_status=False,
            # when
        )

        # then
        assert done_result.startswith(" - [x]")
        assert blocked_result.startswith(" - [-]")

    def test_format_task_code_review_renders_as_unchecked(self) -> None:
        # given: code review only ever shows [ ] (pending) or [x] (reviewed/merged)
        formatter = TaskFormatter()
        task = Task(id="1", description="Review PR", status=Status.CODE_REVIEW)

        # when
        result = formatter.format_task(task, with_name=False, with_status=False)

        # then
        assert result.startswith(" - [ ]")

    def test_status_checkbox_char_maps_code_review_to_space(self) -> None:
        assert TaskFormatter.status_checkbox_char(Status.CODE_REVIEW) == " "
        assert TaskFormatter.status_checkbox_char(Status.DONE) == "x"

    def test_format_tasks_joins_lines(self, mocker: MockerFixture) -> None:
        # given
        formatter = TaskFormatter()
        logger = mocker.patch("taskjournal.repositories.task_formatter.logger")
        tasks = [
            Task(id="1", description="Task A", status=Status.TODO),
            Task(id="2", description="Task B", status=Status.DONE),
        ]

        # when
        result = formatter.format_tasks(tasks)

        # then
        assert "\n" in result
        assert "Task A" in result
        assert "Task B" in result
        logger.debug.assert_called_once_with(tasks)
