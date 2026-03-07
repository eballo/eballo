from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from taskjournal.models.task import Status
from taskjournal.services.jira import JiraService


class _FakeResponse:
    def __init__(self, payload=None, status_code=200, raise_exc=None):
        self._payload = payload or {}
        self.status_code = status_code
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, response=None, get_exc=None):
        self._response = response
        self._get_exc = get_exc
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self._get_exc:
            raise self._get_exc
        return self._response


def _init_service(mocker):
    mocker.patch("taskjournal.services.jira.JIRA", return_value=mocker.MagicMock())
    return JiraService()


def test_init_success_creates_jira_client(mocker):
    jira_client = mocker.MagicMock()
    jira_ctor = mocker.patch("taskjournal.services.jira.JIRA", return_value=jira_client)

    service = JiraService()

    assert service.jira is jira_client
    jira_ctor.assert_called_once_with(server=service.base_url, basic_auth=service.auth)


def test_init_failure_sets_jira_none(mocker):
    mocker.patch("taskjournal.services.jira.JIRA", side_effect=RuntimeError("boom"))

    service = JiraService()

    assert service.jira is None


def test_get_active_sprint_returns_none_when_unavailable(mocker):
    service = _init_service(mocker)
    service.jira = None

    assert service.get_active_sprint() is None


def test_get_active_sprint_returns_active_sprint(mocker):
    service = _init_service(mocker)
    inactive = SimpleNamespace(state="closed")
    active = SimpleNamespace(state="active", id=7)
    service.jira.sprints.return_value = [inactive, active]

    sprint = service.get_active_sprint()

    assert sprint is active


def test_get_active_sprint_handles_errors(mocker):
    service = _init_service(mocker)
    service.jira.sprints.side_effect = RuntimeError("nope")

    assert service.get_active_sprint() is None


@pytest.mark.asyncio
async def test_current_sprint_helper_queries(mocker):
    service = _init_service(mocker)
    service._get_tasks_in_sprint = AsyncMock(return_value=[])

    await service.get_current_sprint_tasks_not_done_assigned_to_me()
    await service.get_current_sprint_tasks_all_assigned_to_me()
    await service.get_current_sprint_tasks()
    await service.get_current_sprint_tasks_in_code_review()

    assert service._get_tasks_in_sprint.await_args_list[0].args == (
        "assignee = currentUser() AND status != Done",
    )
    assert service._get_tasks_in_sprint.await_args_list[1].args == (
        "assignee = currentUser()",
    )
    assert service._get_tasks_in_sprint.await_args_list[2].args == ("",)
    assert service._get_tasks_in_sprint.await_args_list[3].args == (
        "status = 'CODE REVIEW' and assignee != currentUser()",
    )


@pytest.mark.asyncio
async def test_last_month_and_six_month_queries(mocker):
    service = _init_service(mocker)
    service._get_issues = AsyncMock(return_value=[])
    fixed_now = datetime(2026, 3, 7, 12, 0, 0)
    mocker.patch("taskjournal.services.jira.datetime", **{"now.return_value": fixed_now})

    await service.get_current_tasks_assigned_to_me_last_month()
    await service.get_current_tasks_assigned_to_me_last_6_months()

    assert (
        service._get_issues.await_args_list[0].args[0]
        == "assignee = currentUser() AND updated >= 2026-02-05"
    )
    assert (
        service._get_issues.await_args_list[1].args[0]
        == "assignee = currentUser() AND updated >= 2025-09-08"
    )


@pytest.mark.asyncio
async def test_get_tasks_in_sprint_no_active_sprint_returns_empty(mocker):
    service = _init_service(mocker)
    mocker.patch.object(service, "get_active_sprint", return_value=None)

    assert await service._get_tasks_in_sprint("x = y") == []


@pytest.mark.asyncio
async def test_get_tasks_in_sprint_builds_jql_with_and_without_extra(mocker):
    service = _init_service(mocker)
    mocker.patch.object(service, "get_active_sprint", return_value=SimpleNamespace(id=42))
    service._get_issues = AsyncMock(return_value=["ok"])

    out_without = await service._get_tasks_in_sprint("")
    out_with = await service._get_tasks_in_sprint("assignee = currentUser()")

    assert out_without == ["ok"]
    assert out_with == ["ok"]
    assert service._get_issues.await_args_list[0].args == ("sprint = 42",)
    assert service._get_issues.await_args_list[1].args == (
        "sprint = 42 AND assignee = currentUser()",
    )


@pytest.mark.asyncio
async def test_fetch_repo_returns_none_for_403_404(mocker):
    service = _init_service(mocker)

    r404 = _FakeAsyncClient(response=_FakeResponse(status_code=404))
    r403 = _FakeAsyncClient(response=_FakeResponse(status_code=403))

    assert await service._fetch_repo_from_dev_status(r404, "1", "BE-1") is None
    assert await service._fetch_repo_from_dev_status(r403, "1", "BE-1") is None


@pytest.mark.asyncio
async def test_fetch_repo_returns_open_pr_matching_issue_key(mocker):
    service = _init_service(mocker)
    payload = {
        "detail": [
            {
                "pullRequests": [
                    {"status": "OPEN", "name": "BE-77 feature", "url": "http://pr/77"}
                ]
            }
        ]
    }
    client = _FakeAsyncClient(response=_FakeResponse(payload=payload, status_code=200))

    result = await service._fetch_repo_from_dev_status(client, "77", "BE-77")

    assert result == "http://pr/77"


@pytest.mark.asyncio
async def test_fetch_repo_returns_none_when_no_matching_pr(mocker):
    service = _init_service(mocker)
    payload = {
        "detail": [
            {
                "pullRequests": [
                    {"status": "CLOSED", "name": "BE-77 feature", "url": "http://pr/77"},
                    {"status": "OPEN", "name": "OTHER-1", "url": "http://pr/1"},
                ]
            }
        ]
    }
    client = _FakeAsyncClient(response=_FakeResponse(payload=payload))

    result = await service._fetch_repo_from_dev_status(client, "77", "BE-77")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_repo_handles_client_exceptions(mocker):
    service = _init_service(mocker)
    client = _FakeAsyncClient(get_exc=RuntimeError("network"))

    result = await service._fetch_repo_from_dev_status(client, "7", "BE-7")

    assert result is None


@pytest.mark.asyncio
async def test_get_issues_builds_tasks_and_hydrates_urls(mocker):
    service = _init_service(mocker)

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

    fake_client = _FakeAsyncClient(response=_FakeResponse(payload=payload))
    mocker.patch("taskjournal.services.jira.AsyncClient", return_value=fake_client)
    service._fetch_repo_from_dev_status = AsyncMock(
        side_effect=[RuntimeError("boom"), None, "http://pr/103"]
    )

    tasks = await service._get_issues("assignee = currentUser()")

    assert len(tasks) == 3
    assert tasks[0].key == "BE-1"
    assert tasks[0].description == "Task One"
    assert tasks[0].status == Status.DONE
    assert tasks[0].epic.key == "EP-1"
    assert tasks[0].assignee.name == "Alice"
    assert tasks[0].github is None

    assert tasks[1].key is None
    assert tasks[1].status == Status.IN_PROGRESS  # default mapping
    assert tasks[1].assignee is None
    assert tasks[1].epic is None

    assert tasks[2].key == "BE-3"
    assert tasks[2].status == Status.BLOCKED
    assert tasks[2].assignee.name == "Bob"
    assert tasks[2].github == "http://pr/103"


@pytest.mark.asyncio
async def test_get_issues_returns_empty_when_request_fails(mocker):
    service = _init_service(mocker)

    response = _FakeResponse(raise_exc=RuntimeError("http 500"))
    fake_client = _FakeAsyncClient(response=response)
    mocker.patch("taskjournal.services.jira.AsyncClient", return_value=fake_client)

    tasks = await service._get_issues("assignee = currentUser()")

    assert tasks == []


def test_sanitize_description():
    assert JiraService.sanitize_description(None) == ""
    assert JiraService.sanitize_description("Fix <this> and >that<") == "Fix this and that"


@pytest.mark.parametrize(
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
def test_get_task_status(jira_status, expected):
    assert JiraService.get_task_status(jira_status) == expected
