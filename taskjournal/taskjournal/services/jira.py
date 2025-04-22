from typing import List, Dict

from jira import JIRA

from taskjournal.config import JIRA_ORGANIZATION, JIRA_EMAIL, JIRA_API_TOKEN
from taskjournal.services.logger import logger


class JiraService:
    def __init__(self):
        self.jira = JIRA(
            server=f"https://{JIRA_ORGANIZATION}.atlassian.net",
            basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN),
        )

    def get_current_sprint_issues(self, board_id: int) -> List[Dict]:
        sprints = self.jira.sprints(board_id)
        active_sprint = next((s for s in sprints if s.state == "active"), None)

        if not active_sprint:
            print("No active sprint found.")
            return []

        jql = f"sprint = {active_sprint.id} AND assignee = currentUser()"
        issues = self.jira.search_issues(jql, maxResults=100)

        logger.info(f"Found {len(issues)} issues in the current sprint.")

        return [
            {
                "key": issue.key,
                "summary": issue.fields.summary,
                "timespent_hours": (issue.fields.timespent or 0) / 3600,
                "status": issue.fields.status.name,
            }
            for issue in issues
        ]
