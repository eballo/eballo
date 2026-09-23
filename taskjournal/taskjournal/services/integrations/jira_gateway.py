from json import dumps
from typing import Any, cast

from httpx import AsyncClient
from jira import JIRA

from taskjournal.services.logger import logger


class JiraGateway:
    """Own Jira Cloud authentication and remote requests."""

    def __init__(self, api_token: str, email: str, organization: str) -> None:
        self.base_url = f"https://{organization}.atlassian.net"
        self.auth = (email, api_token)
        self.jira: JIRA | None = None
        if api_token == "your-jira-key":
            return
        try:
            self.jira = JIRA(server=self.base_url, basic_auth=self.auth)
            logger.debug("Jira successfully initialized")
        except Exception as e:
            logger.error(f"Failed to connect to Jira: {e}")

    def sprints(self, board_id: str) -> list[Any]:
        if self.jira is None:
            raise RuntimeError("Jira service unavailable.")
        return cast(list[Any], self.jira.sprints(board_id, state="active"))

    def client(self) -> AsyncClient:
        return AsyncClient(timeout=15.0, auth=self.auth)

    async def search(self, client: AsyncClient, jql: str) -> dict[str, Any]:
        resp = await client.get(
            f"{self.base_url}/rest/api/3/search/jql",
            params={
                "jql": jql,
                "startAt": "0",
                "maxResults": "100",
                "fields": "summary,status,assignee,parent,issuetype",
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())

    async def fetch_repo_from_dev_status(
        self, client: AsyncClient, issue_id: str, issue_key: str
    ) -> str | None:
        try:
            resp = await client.get(
                f"{self.base_url}/rest/dev-status/latest/issue/detail",
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

            for detail in data.get("detail", []):
                for pull_request in detail.get("pullRequests", []):
                    if (
                        pull_request["status"] in ("OPEN", "MERGED")
                        and issue_key in pull_request["name"]
                    ):
                        return str(pull_request["url"])
        except Exception as e:
            logger.debug(f"fetch failed for {issue_id}: {e}")
        return None
