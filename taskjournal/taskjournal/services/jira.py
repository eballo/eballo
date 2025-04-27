import uuid
from typing import List

from jira import JIRA
from jira.resources import Sprint

from taskjournal.config import (
    JIRA_ORGANIZATION,
    JIRA_EMAIL,
    JIRA_API_TOKEN,
    JIRA_BOARD_ID,
)
from taskjournal.models.task import Task, Status
from taskjournal.services.logger import logger


class JiraService:
    def __init__(self):
        self.board_id = JIRA_BOARD_ID
        self.jira = JIRA(
            server=f"https://{JIRA_ORGANIZATION}.atlassian.net",
            basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN),
        )

    def get_active_sprint(self) -> Sprint | None:
        sprints = self.jira.sprints(self.board_id)
        active_sprint = next((s for s in sprints if s.state == "active"), None)

        if not active_sprint:
            logger.warning("No active sprint found.")
            return None

        return active_sprint

    def get_current_sprint_tasks_not_done_assigned_to_me(self) -> List[Task]:
        active_sprint = self.get_active_sprint()
        if not active_sprint:
            return []

        jql = f"sprint = {active_sprint.id} AND assignee = currentUser() AND status != Done"
        return self._get_issues(jql)

    def get_current_sprint_tasks_all_assigned_to_me(self) -> List[Task]:
        active_sprint = self.get_active_sprint()
        if not active_sprint:
            return []

        jql = f"sprint = {active_sprint.id} AND assignee = currentUser()"
        return self._get_issues(jql)

    def get_current_sprint_tasks(self) -> List[Task]:
        active_sprint = self.get_active_sprint()
        if not active_sprint:
            return []

        jql = f"sprint = {active_sprint.id}"
        return self._get_issues(jql)

    def get_current_sprint_tasks_in_code_review(self) -> List[Task]:
        active_sprint = self.get_active_sprint()
        if not active_sprint:
            return []

        jql = f"sprint = {active_sprint.id} AND status = 'CODE REVIEW' and assignee != currentUser()"
        return self._get_issues(jql)

    def _get_issues(self, jql):
        issues = self.jira.search_issues(jql, maxResults=100)
        return [
            Task(
                id=str(uuid.uuid4()),
                key=issue.key,
                description=issue.fields.summary,
                link=f"https://{JIRA_ORGANIZATION}.atlassian.net/browse/{issue.key}",
                status=self.get_task_status(issue),
            )
            for issue in issues
        ]

    def get_task_status(self, issue):
        status_mapping = {
            "TO DO": Status.TODO,
            "IN PROGRESS": Status.IN_PROGRESS,
            "DONE": Status.DONE,
            "BLOCKED": Status.BLOCKED,
            "CODE REVIEW": Status.CODE_REVIEW,
        }
        jira_status = issue.fields.status.name
        return status_mapping.get(jira_status, Status.IN_PROGRESS)
