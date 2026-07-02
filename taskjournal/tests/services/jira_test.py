from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from pytest import mark
from pytest_mock import MockerFixture

from taskjournal.models.task import Status
from taskjournal.services.integrations.jira import JiraService


class _FakeResponse:
    def __init__(
        self,
        payload: dict[str, Any] | None = None,
        status_code: int = 200,
        raise_exc: Exception | None = None,
    ) -> None:
        self._payload = payload or {}
        self.status_code = status_code
        self._raise_exc = raise_exc

    def raise_for_status(self) -> None:
        if self._raise_exc:
            raise self._raise_exc

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeAsyncClient:
    def __init__(
        self,
        response: _FakeResponse | None = None,
        get_exc: Exception | None = None,
    ) -> None:
        self._response = response
        self._get_exc = get_exc
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        return None

    async def get(self, *args: Any, **kwargs: Any) -> _FakeResponse | None:
        self.calls.append((args, kwargs))
        if self._get_exc:
            raise self._get_exc
        return self._response


class TestJira:

    def test_init_success_creates_jira_client(self, mocker: MockerFixture) -> None:
        # given
        jira_client = mocker.MagicMock()
        jira_ctor = mocker.patch(
            "taskjournal.services.integrations.jira.JIRA", return_value=jira_client
        )

        # when
        service = JiraService(api_token="tok", email="e@e.com", board_id="BD", organization="org")

        # then
        assert service.jira is jira_client
        jira_ctor.assert_called_once_with(
            server=service.base_url, basic_auth=service.auth
        )

    def test_init_failure_sets_jira_none(self, mocker: MockerFixture) -> None:
        # given
        mocker.patch("taskjournal.services.integrations.jira.JIRA", side_effect=RuntimeError("boom"))

        # when
        service = JiraService(api_token="tok", email="e@e.com", board_id="BD", organization="org")

        # then
        assert service.jira is None

    def test_init_skips_connection_when_unconfigured(self, mocker: MockerFixture) -> None:
        jira_ctor = mocker.patch("taskjournal.services.integrations.jira.JIRA")

        service = JiraService(
            api_token="your-jira-key", email="e@e.com", board_id="BD", organization="org"
        )

        jira_ctor.assert_not_called()
        assert service.jira is None

    def test_get_active_sprint_returns_none_when_unavailable(
        self,
        jira_service: JiraService,
    ) -> None:
        # when
        jira_service.jira = None

        # then
        assert jira_service.get_active_sprint() is None

    def test_get_active_sprint_returns_active_sprint(
        self, jira_service: JiraService
    ) -> None:
        # given
        active = SimpleNamespace(state="active", id=7, name="Sprint 2")
        jira_service.jira.sprints.return_value = [active]

        # when
        sprint = jira_service.get_active_sprint()

        # then
        assert sprint is active
        jira_service.jira.sprints.assert_called_with(
            jira_service.board_id, state="active"
        )

    def test_get_active_sprint_returns_active_sprint_from_raw(
        self, jira_service: JiraService
    ) -> None:
        # given
        active = SimpleNamespace(raw={"state": "active"}, id=8, name="Sprint 3")
        # remove 'state' attribute if it exists to test raw fallback
        if hasattr(active, "state"):
            delattr(active, "state")
        jira_service.jira.sprints.return_value = [active]

        # when
        sprint = jira_service.get_active_sprint()

        # then
        assert sprint is active

    def test_get_active_sprint_handles_errors(self, jira_service: JiraService) -> None:
        # when
        jira_service.jira.sprints.side_effect = RuntimeError("nope")

        # then
        assert jira_service.get_active_sprint() is None

    @mark.asyncio
    async def test_current_sprint_helper_queries(
        self, jira_service: JiraService, mocker: MockerFixture
    ) -> None:
        # given
        mock_get_tasks = mocker.patch.object(
            jira_service,
            "_get_tasks_in_sprint",
            new_callable=AsyncMock,
            return_value=[],
        )

        await jira_service.get_current_sprint_tasks_not_done_assigned_to_me()
        await jira_service.get_current_sprint_tasks_all_assigned_to_me()
        await jira_service.get_current_sprint_tasks()
        # when
        await jira_service.get_current_sprint_tasks_in_code_review()

        # then
        assert mock_get_tasks.await_args_list[0].args == (
            "assignee = currentUser() AND status != Done",
        )
        assert mock_get_tasks.await_args_list[1].args == ("assignee = currentUser()",)
        assert mock_get_tasks.await_args_list[2].args == ("",)
        assert mock_get_tasks.await_args_list[3].args == (
            "status = 'CODE REVIEW' and assignee != currentUser()",
        )

    @mark.asyncio
    async def test_last_month_and_six_month_queries(
        self, jira_service: JiraService, mocker: MockerFixture
    ) -> None:
        # given
        mock_get_issues = mocker.patch.object(
            jira_service, "_get_issues", new_callable=AsyncMock, return_value=[]
        )
        # when
        fixed_now = datetime(2026, 3, 7, 12, 0, 0)
        mocker.patch(
            "taskjournal.services.integrations.jira.datetime", **{"now.return_value": fixed_now}
        )

        await jira_service.get_current_tasks_assigned_to_me_last_month()
        await jira_service.get_current_tasks_assigned_to_me_last_6_months()

        # then
        assert (
            mock_get_issues.await_args_list[0].args[0]
            == "assignee = currentUser() AND updated >= 2026-02-05"
        )
        assert (
            mock_get_issues.await_args_list[1].args[0]
            == "assignee = currentUser() AND updated >= 2025-09-08"
        )

    @mark.asyncio
    async def test_get_tasks_in_sprint_no_active_sprint_returns_empty(
        self, jira_service: JiraService, mocker: MockerFixture
    ) -> None:
        # when
        mocker.patch.object(jira_service, "get_active_sprint", return_value=None)

        # then
        assert await jira_service._get_tasks_in_sprint("x = y") == []

    @mark.asyncio
    async def test_get_tasks_in_sprint_builds_jql_with_and_without_extra(
        self, jira_service: JiraService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(
            jira_service, "get_active_sprint", return_value=SimpleNamespace(id=42)
        )
        mock_get_issues = mocker.patch.object(
            jira_service, "_get_issues", new_callable=AsyncMock, return_value=["ok"]
        )

        # when
        out_without = await jira_service._get_tasks_in_sprint("")
        out_with = await jira_service._get_tasks_in_sprint("assignee = currentUser()")

        # then
        assert out_without == ["ok"]
        assert out_with == ["ok"]
        assert mock_get_issues.await_args_list[0].args == ("sprint = 42",)
        assert mock_get_issues.await_args_list[1].args == (
            "sprint = 42 AND assignee = currentUser()",
        )

    @mark.asyncio
    async def test_fetch_repo_returns_none_for_403_404(
        self,
        jira_service: JiraService,
    ) -> None:
        # given
        r404 = _FakeAsyncClient(response=_FakeResponse(status_code=404))
        # when
        r403 = _FakeAsyncClient(response=_FakeResponse(status_code=403))

        # then
        assert await jira_service._fetch_repo_from_dev_status(r404, "1", "BE-1") is None
        assert await jira_service._fetch_repo_from_dev_status(r403, "1", "BE-1") is None

    @mark.asyncio
    async def test_fetch_repo_returns_open_pr_matching_issue_key(
        self,
        jira_service: JiraService,
    ) -> None:
        # given
        payload = {
            "detail": [
                {
                    "pullRequests": [
                        {
                            "status": "OPEN",
                            "name": "BE-77 feature",
                            "url": "http://pr/77",
                        }
                    ]
                }
            ]
        }
        client = _FakeAsyncClient(
            response=_FakeResponse(payload=payload, status_code=200)
        )

        # when
        result = await jira_service._fetch_repo_from_dev_status(client, "77", "BE-77")

        # then
        assert result == "http://pr/77"

    @mark.asyncio
    async def test_fetch_repo_returns_none_when_no_matching_pr(
        self,
        jira_service: JiraService,
    ) -> None:
        # given
        payload = {
            "detail": [
                {
                    "pullRequests": [
                        {
                            "status": "CLOSED",
                            "name": "BE-77 feature",
                            "url": "http://pr/77",
                        },
                        {"status": "OPEN", "name": "OTHER-1", "url": "http://pr/1"},
                    ]
                }
            ]
        }
        # when
        client = _FakeAsyncClient(response=_FakeResponse(payload=payload))

        result = await jira_service._fetch_repo_from_dev_status(client, "77", "BE-77")

        # then
        assert result is None

    @mark.asyncio
    async def test_fetch_repo_handles_client_exceptions(
        self,
        jira_service: JiraService,
    ) -> None:
        # given
        client = _FakeAsyncClient(get_exc=RuntimeError("network"))

        # when
        result = await jira_service._fetch_repo_from_dev_status(client, "7", "BE-7")

        # then
        assert result is None

    @mark.asyncio
    async def test_get_issues_builds_tasks_and_hydrates_urls(
        self, jira_service: JiraService, mocker: MockerFixture
    ) -> None:
        # given
        payload = {
            "issues": [
                {"id": "100", "key": "BE-0", "fields": {}},  # skipped
                {
                    "id": "101",
                    "key": "BE-1",
                    "fields": {
                        "summary": "Task <One>",
                        "status": {"name": "Done"},
                        "assignee": {"displayName": "Alice"},
                        "parent": {"key": "EP-1", "fields": {"summary": "Epic one"}},
                    },
                },
                {  # key=None -> no idx mapping
                    "id": "102",
                    "key": None,
                    "fields": {
                        "summary": "Task two",
                        "status": {"name": "Unknown"},
                        "assignee": None,
                        "parent": None,
                    },
                },
                {
                    "id": "103",
                    "key": "BE-3",
                    "fields": {
                        "summary": "Task three",
                        "status": {"name": "BLOCKED"},
                        "assignee": {"displayName": "Bob"},
                        "parent": None,
                    },
                },
            ]
        }

        # when
        fake_client = _FakeAsyncClient(response=_FakeResponse(payload=payload))
        mocker.patch("taskjournal.services.integrations.jira.AsyncClient", return_value=fake_client)
        mocker.patch.object(
            jira_service,
            "_fetch_repo_from_dev_status",
            new_callable=AsyncMock,
            side_effect=[RuntimeError("boom"), None, "http://pr/103"],
        )

        tasks = await jira_service._get_issues("assignee = currentUser()")

        # then
        assert len(tasks) == 3
        assert tasks[0].key == "BE-1"
        assert tasks[0].description == "Task One"
        assert tasks[0].status == Status.DONE
        assert tasks[0].epic is not None
        assert tasks[0].epic.key == "EP-1"
        assert tasks[0].assignee is not None
        assert tasks[0].assignee.name == "Alice"
        assert tasks[0].github is None

        assert tasks[1].key is None
        assert tasks[1].status == Status.IN_PROGRESS  # default mapping
        assert tasks[1].assignee is None
        assert tasks[1].epic is None

        assert tasks[2].key == "BE-3"
        assert tasks[2].status == Status.BLOCKED
        assert tasks[2].assignee is not None
        assert tasks[2].assignee.name == "Bob"
        assert tasks[2].github == "http://pr/103"

    @mark.asyncio
    async def test_get_issues_returns_empty_when_request_fails(
        self, jira_service: JiraService, mocker: MockerFixture
    ) -> None:
        # given
        response = _FakeResponse(raise_exc=RuntimeError("http 500"))
        fake_client = _FakeAsyncClient(response=response)
        mocker.patch("taskjournal.services.integrations.jira.AsyncClient", return_value=fake_client)

        # when
        tasks = await jira_service._get_issues("assignee = currentUser()")

        # then
        assert tasks == []

    def test_sanitize_description(self) -> None:
        # when
        # then
        assert JiraService.sanitize_description("") == ""
        assert (
            JiraService.sanitize_description("Fix <this> and >that<")
            == "Fix this and that"
        )

    @mark.parametrize(
        ("jira_status", "expected"),
        [
            ("TO DO", Status.TODO),
            ("IN PROGRESS", Status.IN_PROGRESS),
            ("DONE", Status.DONE),
            ("BLOCKED", Status.BLOCKED),
            ("CODE REVIEW", Status.CODE_REVIEW),
            ("something-else", Status.IN_PROGRESS),
        ],
    )
    def test_get_task_status(self, jira_status: str, expected: Status) -> None:
        # when
        # then
        assert JiraService.get_task_status(jira_status) == expected
