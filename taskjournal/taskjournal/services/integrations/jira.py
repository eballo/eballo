from __future__ import annotations

from asyncio import gather
from datetime import datetime, timedelta
from json import dumps
from typing import Any

from httpx import AsyncClient
from jira.resources import Sprint

from taskjournal.models.task import Task, Status
from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus
from taskjournal.services.integrations.jira_gateway import JiraGateway
from taskjournal.services.integrations.jira_mapping import JiraTaskMapper
from taskjournal.services.logger import logger

_UNCONFIGURED_TOKEN = "your-jira-key"


class JiraService(BaseService):

    def __init__(
        self,
        api_token: str,
        email: str,
        board_id: str,
        organization: str,
        gateway: JiraGateway | None = None,
        mapper: JiraTaskMapper | None = None,
    ) -> None:
        self.board_id = board_id
        self._api_token = api_token
        self.gateway = gateway if gateway is not None else JiraGateway(api_token, email, organization)
        self.mapper = mapper if mapper is not None else JiraTaskMapper()

    @property
    def base_url(self) -> str:
        return self.gateway.base_url

    @property
    def auth(self) -> tuple[str, str]:
        return self.gateway.auth

    @property
    def jira(self) -> Any:
        return self.gateway.jira

    @jira.setter
    def jira(self, value: Any) -> None:
        self.gateway.jira = value

    @property
    def name(self) -> str:
        return "Jira"

    def health_check(self) -> HealthCheckResult:
        if self._api_token == _UNCONFIGURED_TOKEN:
            return HealthCheckResult(
                ServiceStatus.UNCONFIGURED,
                "JIRA_API_TOKEN not configured — Jira integration disabled",
            )
        if self.jira is None:
            return HealthCheckResult(
                ServiceStatus.ERROR,
                f"Could not connect to {self.base_url}",
            )
        return HealthCheckResult(
            ServiceStatus.OK,
            f"Connected ({self.base_url}, board: {self.board_id})",
        )

    def get_active_sprint(self) -> Sprint | None:
        if not self.jira:
            logger.warning("Jira service unavailable.")
            return None
        try:
            # Only fetch active sprints to avoid pagination issues
            sprints = self.gateway.sprints(self.board_id)
            logger.debug(
                f"Fetched {len(sprints)} active sprints for board {self.board_id}"
            )
            for s in sprints:
                # Jira Sprint objects might have 'state' or 'raw["state"]'
                state = getattr(s, "state", None)
                if state is None and hasattr(s, "raw"):
                    logger.debug(f"Retrieving state from raw data for sprint {s.id}")
                    state = s.raw.get("state")

                if state == "active":
                    sprint_name = getattr(s, "name", "Unknown")
                    logger.debug(f"Found active sprint: {sprint_name} (id: {s.id})")
                    return s  # type: ignore[no-any-return]
            return None
        except Exception as e:
            logger.error(f"Error fetching active sprint: {e}")
            return None

    async def get_current_sprint_tasks_not_done_assigned_to_me(self) -> list[Task]:
        return await self._get_tasks_in_sprint(
            "assignee = currentUser() AND status != Done"
        )

    async def get_current_sprint_tasks_all_assigned_to_me(self) -> list[Task]:
        return await self._get_tasks_in_sprint("assignee = currentUser()")

    async def get_current_sprint_tasks(self) -> list[Task]:
        return await self._get_tasks_in_sprint("")

    async def get_current_sprint_tasks_in_code_review(self) -> list[Task]:
        return await self._get_tasks_in_sprint(
            "status = 'CODE REVIEW' and assignee != currentUser()"
        )

    async def get_current_tasks_assigned_to_me_last_month(self) -> list[Task]:
        return await self._get_issues(self._recent_tasks_jql(30))

    async def get_current_tasks_assigned_to_me_last_6_months(self) -> list[Task]:
        return await self._get_issues(self._recent_tasks_jql(180))

    async def get_current_tasks_assigned_to_me_last_quarter(self) -> list[Task]:
        return await self._get_issues(self._recent_tasks_jql(91))

    async def get_current_tasks_assigned_to_me_last_year(self) -> list[Task]:
        return await self._get_issues(self._recent_tasks_jql(365))

    @staticmethod
    def _recent_tasks_jql(days: int) -> str:
        date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return f"assignee = currentUser() AND updated >= {date}"

    @staticmethod
    def _sprint_jql(sprint_id: str, extra_jql: str) -> str:
        return f"sprint = {sprint_id}" + (f" AND {extra_jql}" if extra_jql else "")

    async def _get_tasks_in_sprint(self, extra_jql: str) -> list[Task]:
        active_sprint = self.get_active_sprint()
        if not active_sprint:
            logger.debug("No active sprint found, skipping task retrieval")
            return []

        return await self._get_issues(self._sprint_jql(str(active_sprint.id), extra_jql))

    async def _fetch_repo_from_dev_status(
        self, client: AsyncClient, issue_id: str, issue_key: str
    ) -> str | None:
        return await self.gateway.fetch_repo_from_dev_status(client, issue_id, issue_key)

    async def _get_issues(self, jql: str) -> list[Task]:
        """
        Calls Jira Cloud API v3 `/rest/api/3/search/jql` asynchronously with httpx.
        Falls back gracefully if Jira is unavailable.
        """
        logger.debug(f"JQL Query: {jql}")

        try:
            async with self.gateway.client() as client:
                data = await self.gateway.search(client, jql)
                issues = data.get("issues", []) or []

                logger.debug(f"Total issues found: {len(issues)}")
                logger.debug(dumps(data, indent=2))

                # Build Task objects (without GitHub), keep id/key for hydration
                tasks: list[Task] = []
                idx_by_key: dict[str, int] = {}  # key -> index in tasks

                for issue in issues:
                    task = self.mapper.map_issue(issue, self.base_url)
                    if task is None:
                        continue
                    tasks.append(task)
                    if task.key:
                        idx_by_key[task.key] = len(tasks) - 1

                # Concurrently hydrate GitHub repo URLs
                async def _one(issue_obj: dict[str, Any]) -> tuple[str | None, str | None]:
                    issue_id = issue_obj.get("id")
                    issue_key = issue_obj.get("key")
                    if not (issue_id and issue_key):
                        return issue_key, None
                    try:
                        repo_url = await self._fetch_repo_from_dev_status(
                            client, str(issue_id), str(issue_key)
                        )
                        return str(issue_key), repo_url
                    except Exception as e:
                        logger.debug(f"Failed to resolve repo for {issue_key}: {e}")
                        return issue_key, None

                results: list[tuple[str | None, str | None]] = list(await gather(
                    *[_one(iss) for iss in issues], return_exceptions=False
                ))

                for issue_key, repo_url in results:
                    logger.debug(f"Issue: {issue_key}: {repo_url} ")
                    if issue_key and repo_url and issue_key in idx_by_key:
                        tasks[idx_by_key[issue_key]].github = repo_url

                return tasks

        except Exception as e:
            logger.error(f"Jira API request failed: {e}")
            return []

    @staticmethod
    def sanitize_description(text: str) -> str:
        return JiraTaskMapper.sanitize_description(text)

    @staticmethod
    def get_task_status(jira_status: str) -> Status:
        return JiraTaskMapper.get_task_status(jira_status)
