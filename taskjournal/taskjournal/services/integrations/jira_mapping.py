from re import sub
from uuid import uuid4
from typing import Any

from taskjournal.models.task import Epic, Status, Task, User


class JiraTaskMapper:
    @staticmethod
    def sanitize_description(text: str) -> str:
        if not text:
            return ""
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

    def map_issue(self, issue: dict[str, Any], base_url: str) -> Task | None:
        fields = issue.get("fields", {}) or {}
        if not fields:
            return None

        epic = None
        parent = fields.get("parent")
        if parent:
            epic = Epic(
                key=parent.get("key"),
                summary=parent.get("fields", {}).get("summary"),
            )

        assignee = fields.get("assignee")
        user = User(name=assignee["displayName"]) if assignee else None

        return Task(
            id=str(uuid4()),
            key=issue.get("key"),
            description=self.sanitize_description(fields.get("summary") or ""),
            link=f"{base_url}/browse/{issue.get('key')}",
            status=self.get_task_status(fields.get("status", {}).get("name", "")),
            epic=epic,
            assignee=user,
        )