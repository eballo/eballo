from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import httpx
from gidgethub.httpx import GitHubAPI

from taskjournal.config import GIT_HUB_TOKEN, GIT_HUB_ORGANIZATION_NAME
from taskjournal.models.github import RepoCommitStat
from taskjournal.services.logger import logger


class GithubService:
    """
    Async GitHub service using gidgethub + httpx.
    Provides commit statistics for repositories in an organization.
    """

    def __init__(
        self, token: str = GIT_HUB_TOKEN, org_name: str = GIT_HUB_ORGANIZATION_NAME
    ):
        self.token = token
        self.org_name = org_name
        self.client: httpx.AsyncClient = httpx.AsyncClient()
        try:
            self.gh: Optional[GitHubAPI] = GitHubAPI(
                self.client, requester="taskjournal", oauth_token=self.token
            )
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            self.gh = None

    async def close(self) -> None:
        """Gracefully close the underlying httpx client."""
        if self.client:
            await self.client.aclose()

    # --- GitHub API helpers ---
    async def get_user(self) -> Optional[str]:
        if not self.gh:
            logger.error("GitHub client not initialized.")
            return None
        try:
            user = await self.gh.getitem("/user")
            return user.get("login")
        except Exception as e:
            logger.error(f"Failed to fetch user: {e}")
            return None

    async def get_org_commit_stats(
        self,
        since_date: Optional[datetime] = None,
        only_contributed: bool = False,
    ) -> Optional[list[RepoCommitStat]]:
        if not self.gh:
            logger.error("GitHub client not initialized.")
            return None

        username = await self.get_user()
        if not username:
            return None

        if since_date is None:
            since_date = datetime(datetime.today().year, 1, 1)

        since_str = since_date.isoformat()
        logger.info(
            f"Gathering commit stats since {since_date.date()} "
            f"for user '{username}' in org '{self.org_name}' "
            f"(only_contributed={only_contributed})..."
        )

        commit_stats: list[RepoCommitStat] = []

        try:
            async for repo in self.gh.getiter(f"/orgs/{self.org_name}/repos"):
                repo_name = repo["name"]

                try:
                    # Count user commits
                    user_count = 0
                    async for _ in self.gh.getiter(
                        f"/repos/{self.org_name}/{repo_name}/commits?author={username}&since={since_str}"
                    ):
                        user_count += 1

                    if only_contributed and user_count == 0:
                        continue

                    # Count all commits
                    total_count = 0
                    async for _ in self.gh.getiter(
                        f"/repos/{self.org_name}/{repo_name}/commits?since={since_str}"
                    ):
                        total_count += 1

                    if total_count == 0:
                        continue

                    percentage = round((user_count / total_count) * 100, 2)

                    commit_stats.append(
                        RepoCommitStat(
                            repo=repo_name,
                            your_commits=user_count,
                            total_commits=total_count,
                            percentage=percentage,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Skipping repo '{repo_name}' due to error: {e}")

        except Exception as e:
            logger.error(f"Failed to fetch repos for org '{self.org_name}': {e}")
            return None

        if not commit_stats:
            logger.info("No contributions found.")
            return None

        commit_stats.sort(key=lambda r: r.percentage, reverse=True)
        return commit_stats

    # --- summary helpers ---
    async def get_contributions_last_6_months(self) -> str:
        last_six_months = datetime.now() - timedelta(days=180)
        stats = await self.get_org_commit_stats(
            since_date=last_six_months, only_contributed=True
        )
        return self.get_commit_stats_summary(stats)

    async def get_contributions_last_month(self) -> str:
        last_month = datetime.now() - timedelta(days=30)
        stats = await self.get_org_commit_stats(
            since_date=last_month, only_contributed=True
        )
        return self.get_commit_stats_summary(stats)

    @staticmethod
    def get_commit_stats_summary(commit_stats: Optional[list[RepoCommitStat]]) -> str:
        if not commit_stats:
            return "No commit stats to display."

        lines = [
            f"{stat.repo}: {stat.your_commits}/{stat.total_commits} commits ({stat.percentage}%)"
            for stat in commit_stats
        ]

        total_user_commits = sum(r.your_commits for r in commit_stats)
        total_all_commits = sum(r.total_commits for r in commit_stats)
        overall_percentage = (
            round((total_user_commits / total_all_commits) * 100, 2)
            if total_all_commits
            else 0
        )

        lines.append("\n📊 Overall Contribution Summary:")
        lines.append(f"   Your commits: {total_user_commits}")
        lines.append(f"   Org total commits: {total_all_commits}")
        lines.append(f"   Your overall contribution: {overall_percentage}%")

        return "\n".join(lines)

    @staticmethod
    def print_commit_stats(commit_stats: Optional[list[RepoCommitStat]]) -> None:
        """Print commit statistics in a formatted table using the logger."""
        if not commit_stats:
            logger.info("No commit stats to display.")
            return

        for stat in commit_stats:
            logger.info(
                f"{stat.repo}: {stat.your_commits}/{stat.total_commits} commits "
                f"({stat.percentage}%)"
            )

        total_user_commits = sum(r.your_commits for r in commit_stats)
        total_all_commits = sum(r.total_commits for r in commit_stats)
        overall_percentage = (
            round((total_user_commits / total_all_commits) * 100, 2)
            if total_all_commits
            else 0
        )

        logger.info("\n📊 Overall Contribution Summary:")
        logger.info(f"   Your commits: {total_user_commits}")
        logger.info(f"   Org total commits: {total_all_commits}")
        logger.info(f"   Your overall contribution: {overall_percentage}%")
