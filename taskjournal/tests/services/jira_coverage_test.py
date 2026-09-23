from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, call

from pytest import mark
from pytest_mock import MockerFixture

from taskjournal.services.base import HealthCheckResult, ServiceStatus
from taskjournal.services.integrations.jira import JiraService


def test_health_check_reports_unconfigured_token_before_connection(
    jira_service: JiraService,
) -> None:
    service = JiraService(
        api_token="your-jira-key",
        email="test@test.com",
        board_id="TEST",
        organization="testorg",
        gateway=jira_service.gateway,
    )

    assert service.jira is not None
    assert service.name == "Jira"
    assert service.health_check() == HealthCheckResult(
        ServiceStatus.UNCONFIGURED,
        "JIRA_API_TOKEN not configured — Jira integration disabled",
    )


def test_health_check_reports_connection_error(jira_service: JiraService) -> None:
    jira_service.jira = None

    assert jira_service.health_check() == HealthCheckResult(
        ServiceStatus.ERROR,
        "Could not connect to https://testorg.atlassian.net",
    )


def test_health_check_reports_connected_board(jira_service: JiraService) -> None:
    assert jira_service.jira is not None

    assert jira_service.health_check() == HealthCheckResult(
        ServiceStatus.OK,
        "Connected (https://testorg.atlassian.net, board: TEST)",
    )


@mark.parametrize(
    "sprints",
    [
        [],
        [
            SimpleNamespace(id=1, state="future"),
            SimpleNamespace(id=2, raw={"state": "closed"}),
        ],
    ],
)
def test_get_active_sprint_returns_none_without_active_state(
    jira_service: JiraService, sprints: list[SimpleNamespace]
) -> None:
    jira_service.jira.sprints.return_value = sprints

    assert jira_service.get_active_sprint() is None
    jira_service.jira.sprints.assert_called_once_with("TEST", state="active")


def test_get_active_sprint_skips_inactive_sprints(
    jira_service: JiraService,
) -> None:
    active = SimpleNamespace(id=3, raw={"state": "active"}, name="Current")
    jira_service.jira.sprints.return_value = [
        SimpleNamespace(id=1, state="future"),
        SimpleNamespace(id=2, raw={"state": "closed"}),
        active,
    ]

    assert jira_service.get_active_sprint() is active
    jira_service.jira.sprints.assert_called_once_with("TEST", state="active")


@mark.asyncio
async def test_quarter_and_year_queries_return_mapped_results(
    jira_service: JiraService, mocker: MockerFixture
) -> None:
    mocker.patch(
        "taskjournal.services.integrations.jira.datetime",
        **{"now.return_value": datetime(2026, 3, 7, 12)},
    )
    quarter_tasks = [mocker.sentinel.quarter_task]
    year_tasks = [mocker.sentinel.year_task]
    get_issues = mocker.patch.object(
        jira_service,
        "_get_issues",
        new_callable=AsyncMock,
        side_effect=[quarter_tasks, year_tasks],
    )

    assert (
        await jira_service.get_current_tasks_assigned_to_me_last_quarter()
        is quarter_tasks
    )
    assert await jira_service.get_current_tasks_assigned_to_me_last_year() is year_tasks
    assert get_issues.await_args_list == [
        call("assignee = currentUser() AND updated >= 2025-12-06"),
        call("assignee = currentUser() AND updated >= 2025-03-07"),
    ]
