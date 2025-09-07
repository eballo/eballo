import uuid
from datetime import datetime, timedelta
from typing import List

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

    def get_current_tasks_assigned_to_me_last_month(self) -> List[Task]:
        last_month = datetime.now() - timedelta(days=30)
        last_month_str = last_month.strftime("%Y-%m-%d")
        jql = f"assignee = currentUser() AND updated >= {last_month_str}"
        return self._get_issues(jql)

    def get_current_tasks_assigned_to_me_last_6_months(self) -> List[Task]:
        six_months_ago = datetime.now() - timedelta(days=180)
        six_months_ago_str = six_months_ago.strftime("%Y-%m-%d")
        jql = f"assignee = currentUser() AND updated >= {six_months_ago_str}"
        return self._get_issues(jql)

    def _get_issues(self, jql):
        issues = self.jira.search_issues(jql, maxResults=100)
        if self.debug:
            logger.debug(f"JQL Query: {jql}")
            logger.debug(f" total issues found: {len(issues)}")

        tasks = []
        for issue in issues:

            epic = None
            parent = getattr(issue.fields, "parent", None)
            if parent:
                epic_issue = self.jira.issue(parent.key)
                epic = Epic(key=epic_issue.key, summary=epic_issue.fields.summary)

            assignee = issue.fields.assignee
            user = User(name=assignee.displayName) if assignee else None

            task = Task(
                id=str(uuid.uuid4()),
                key=issue.key,
                description=issue.fields.summary,
                link=f"https://{JIRA_ORGANIZATION}.atlassian.net/browse/{issue.key}",
                status=self.get_task_status(issue),
                epic=epic,
                assignee=user,
            )
            tasks.append(task)
        return tasks

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
