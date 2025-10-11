from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import List

import httpx
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

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.board_id = JIRA_BOARD_ID
        self.base_url = f"https://{JIRA_ORGANIZATION}.atlassian.net"
        self.auth = (JIRA_EMAIL, JIRA_API_TOKEN)

        try:
            self.jira = JIRA(server=self.base_url, basic_auth=self.auth)
        except Exception as e:
            logger.error(f"Failed to connect to Jira: {e}")
            self.jira = None

    def get_active_sprint(self) -> Sprint | None:
        if not self.jira:
            logger.warning("Jira service unavailable.")
            return None

        try:
            sprints = self.jira.sprints(self.board_id)
            return next((s for s in sprints if s.state == "active"), None)
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
            return []

        jql = f"sprint = {active_sprint.id}"
        if extra_jql:
            jql += f" AND {extra_jql}"

        return await self._get_issues(jql)

    async def _get_issues(self, jql: str) -> List[Task]:
        """
        Calls Jira Cloud API v3 `/rest/api/3/search/jql` asynchronously with httpx.
        Falls back gracefully if Jira is unavailable.
        """
        # FIXME : feature #45 add retrials mechanism
        url = f"{self.base_url}/rest/api/3/search/jql"
        params = {
            "jql": jql,
            "startAt": 0,
            "maxResults": 100,
            "fields": "summary,status,assignee,parent",
        }

        if self.debug:
            logger.debug(f"JQL Query: {jql}")

        try:
            async with httpx.AsyncClient(timeout=15.0, auth=self.auth) as client:
                resp = await client.get(
                    url,
                    params=params,
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
        except Exception as e:
            logger.error(f"Jira API request failed: {e}")
            return []

        data = resp.json()
        issues = data.get("issues", [])

        if self.debug:
            logger.debug(f"Total issues found: {len(issues)}")
            logger.debug(json.dumps(data, indent=2))

        tasks: List[Task] = []
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            if not fields:  # skip if missing
                continue

            # Epic (if parent exists)
            epic = None
            parent = fields.get("parent")
            if parent:
                epic = Epic(
                    key=parent["key"],
                    summary=parent["fields"]["summary"],
                )

            assignee = fields.get("assignee")
            user = User(name=assignee["displayName"]) if assignee else None

            task = Task(
                id=str(uuid.uuid4()),
                key=issue["key"],
                description=fields.get("summary"),
                link=f"{self.base_url}/browse/{issue['key']}",
                status=self.get_task_status(fields["status"]["name"]),
                epic=epic,
                assignee=user,
            )
            tasks.append(task)

        return tasks

    def get_task_status(self, jira_status: str) -> Status:
        status_mapping = {
            "TO DO": Status.TODO,
            "IN PROGRESS": Status.IN_PROGRESS,
            "DONE": Status.DONE,
            "BLOCKED": Status.BLOCKED,
            "CODE REVIEW": Status.CODE_REVIEW,
        }
        return status_mapping.get(jira_status.upper(), Status.IN_PROGRESS)
