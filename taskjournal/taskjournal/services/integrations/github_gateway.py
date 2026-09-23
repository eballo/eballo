from collections.abc import AsyncIterator
from typing import Any

from gidgethub.httpx import GitHubAPI
from httpx import AsyncClient

from taskjournal.services.logger import logger


class GitHubGateway:
    """Own the authenticated GitHub HTTP client and paginated requests."""

    def __init__(self, token: str) -> None:
        self.token = token
        self.client: AsyncClient | None = None
        self.gh: GitHubAPI | None = None

    async def open(self) -> None:
        self.client = AsyncClient()
        try:
            self.gh = GitHubAPI(self.client, requester="taskjournal", oauth_token=self.token)
            logger.debug("Github successfully initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            self.gh = None

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()

    async def getitem(self, path: str) -> Any:
        if self.gh is None:
            raise RuntimeError("GitHub client not initialized.")
        return await self.gh.getitem(path)

    def getiter(self, path: str) -> AsyncIterator[Any]:
        if self.gh is None:
            raise RuntimeError("GitHub client not initialized.")
        return self.gh.getiter(path)

    async def count(self, path: str) -> int:
        count = 0
        async for _ in self.getiter(path):
            count += 1
        return count