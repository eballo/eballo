from __future__ import annotations

from asyncio import gather
from datetime import datetime, timedelta
from json import dumps
from re import sub
from typing import List
from uuid import uuid4

from httpx import AsyncClient
from jira import JIRA
from jira.resources import Sprint

from taskjournal.config import (
    JIRA_ORGANIZATION,
    JIRA_EMAIL,
    JIRA_API_TOKEN,
    JIRA_BOARD_ID,
)
from taskjournal.models.task import Task, Status, Epic, User
from taskjournal.services.logger import logger


class JiraService:

    def __init__(self):
        self.board_id = JIRA_BOARD_ID
        self.base_url = f"https://{JIRA_ORGANIZATION}.atlassian.net"
        self.auth = (JIRA_EMAIL, JIRA_API_TOKEN)

        try:
            self.jira = JIRA(server=self.base_url, basic_auth=self.auth)
            logger.debug("Jira successfully initialized")
        except Exception as e:
            logger.error(f"Failed to connect to Jira: {e}")
            self.jira = None

    def get_active_sprint(self) -> Sprint | None:
        if not self.jira:
            logger.warning("Jira service unavailable.")
            return None
        try:
            # Only fetch active sprints to avoid pagination issues
            sprints = self.jira.sprints(self.board_id, state="active")
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
                    return s
            return None
        except Exception as e:
            logger.error(f"Error fetching active sprint: {e}")
            return None

    async def get_current_sprint_tasks_not_done_assigned_to_me(self) -> List[Task]:
        return await self._get_tasks_in_sprint(
            "assignee = currentUser() AND status != Done"
        )

    async def get_current_sprint_tasks_all_assigned_to_me(self) -> List[Task]:
        return await self._get_tasks_in_sprint("assignee = currentUser()")

    async def get_current_sprint_tasks(self) -> List[Task]:
        return await self._get_tasks_in_sprint("")

    async def get_current_sprint_tasks_in_code_review(self) -> List[Task]:
        return await self._get_tasks_in_sprint(
            "status = 'CODE REVIEW' and assignee != currentUser()"
        )

    async def get_current_tasks_assigned_to_me_last_month(self) -> List[Task]:
        last_month_str = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        jql = f"assignee = currentUser() AND updated >= {last_month_str}"
        return await self._get_issues(jql)

    async def get_current_tasks_assigned_to_me_last_6_months(self) -> List[Task]:
        six_months_ago_str = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
        jql = f"assignee = currentUser() AND updated >= {six_months_ago_str}"
        return await self._get_issues(jql)

    async def _get_tasks_in_sprint(self, extra_jql: str) -> List[Task]:
        active_sprint = self.get_active_sprint()
        if not active_sprint:
            logger.debug("No active sprint found, skipping task retrieval")
            return []

        jql = f"sprint = {active_sprint.id}"
        if extra_jql:
            jql += f" AND {extra_jql}"

        return await self._get_issues(jql)

    async def _fetch_repo_from_dev_status(
        self, client: AsyncClient, issue_id: str, issue_key: str
    ) -> str | None:
        base = f"{self.base_url}/rest/dev-status/latest/issue/detail"
        try:
            resp = await client.get(
                base,
                params={
                    "issueId": issue_id,
                    "applicationType": "GitHub",
                    "dataType": "pullrequest",
                },
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 404 or resp.status_code == 403:
                return None
            resp.raise_for_status()
            data = resp.json() or {}

            logger.debug(f"GitHub - {issue_key} {issue_id}")
            logger.debug(dumps(data, indent=2))

            details = data.get("detail", [])
            for detail in details:
                pull_requests = detail.get("pullRequests", [])
                for pull_request in pull_requests:
                    if (
                        pull_request["status"] == "OPEN"
                        and issue_key in pull_request["name"]
                    ):
                        return pull_request["url"]
        except Exception as e:
            logger.debug(f"fetch failed for {issue_id}: {e}")

        return None

    async def _get_issues(self, jql: str) -> List[Task]:
        """
        Calls Jira Cloud API v3 `/rest/api/3/search/jql` asynchronously with httpx.
        Falls back gracefully if Jira is unavailable.
        """
        url = f"{self.base_url}/rest/api/3/search/jql"
        params = {
            "jql": jql,
            "startAt": 0,
            "maxResults": 100,
            "fields": "summary,status,assignee,parent,issuetype",
        }

        logger.debug(f"JQL Query: {jql}")

        try:
            async with AsyncClient(timeout=15.0, auth=self.auth) as client:
                resp = await client.get(
                    url,
                    params=params,
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()

                data = resp.json()
                issues = data.get("issues", []) or []

                logger.debug(f"Total issues found: {len(issues)}")
                logger.debug(dumps(data, indent=2))

                # Build Task objects (without GitHub), keep id/key for hydration
                tasks: List[Task] = []
                idx_by_key: dict[str, int] = {}  # key -> index in tasks

                for issue in issues:
                    fields = issue.get("fields", {}) or {}
                    if not fields:
                        continue

                    epic = None
                    parent = fields.get("parent")
                    if parent:
                        epic = Epic(
                            key=parent.get("key"),
                            summary=parent.get("fields", {}).get("summary"),
                        )

                    assignee = fields.get("assignee")
                    user = User(name=assignee["displayName"]) if assignee else None

                    task = Task(
                        id=str(uuid4()),
                        key=issue.get("key"),
                        description=self.sanitize_description(fields.get("summary")),
                        link=f"{self.base_url}/browse/{issue.get('key')}",
                        status=self.get_task_status(
                            fields.get("status", {}).get("name", "")
                        ),
                        epic=epic,
                        assignee=user,
                    )
                    tasks.append(task)
                    if task.key:
                        idx_by_key[task.key] = len(tasks) - 1

                # Concurrently hydrate GitHub repo URLs
                async def _one(issue_obj):
                    issue_id = issue_obj.get("id")
                    issue_key = issue_obj.get("key")
                    if not (issue_id and issue_key):
                        return issue_key, None
                    try:
                        repo_url = await self._fetch_repo_from_dev_status(
                            client, issue_id, issue_key
                        )
                        return issue_key, repo_url
                    except Exception as e:
                        logger.debug(f"Failed to resolve repo for {issue_key}: {e}")
                        return issue_key, None

                results = await gather(
                    *[_one(iss) for iss in issues], return_exceptions=False
                )

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
        if not text:
            return ""
        # Remove < and > characters
        return sub(r"[<>]", "", text)

    @staticmethod
    def get_task_status(jira_status: str) -> Status:
        status_mapping = {
            "TO DO": Status.TODO,
            "IN PROGRESS": Status.IN_PROGRESS,
            "DONE": Status.DONE,
            "BLOCKED": Status.BLOCKED,
            "CODE REVIEW": Status.CODE_REVIEW,
        }
        return status_mapping.get(jira_status.upper(), Status.IN_PROGRESS)
