from datetime import datetime, timedelta
from re import match as re_match
from urllib.parse import urlparse

import httpx
from gidgethub.httpx import GitHubAPI

from taskjournal.models.github import RepoCommitStat
from taskjournal.models.task import Status, Task
from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus
from taskjournal.services.logger import logger

_UNCONFIGURED_TOKEN = "your-github-token"


class GithubService(BaseService):
    """Async GitHub service using gidgethub + httpx."""

    def __init__(
        self,
        token: str,
        org_name: str,
    ) -> None:
        self.token = token
        self.org_name = org_name
        self.client: httpx.AsyncClient = httpx.AsyncClient()
        try:
            self.gh: GitHubAPI | None = GitHubAPI(
                self.client, requester="taskjournal", oauth_token=self.token
            )
            logger.debug("Github successfully initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            self.gh = None

    @property
    def name(self) -> str:
        return "GitHub"

    def health_check(self) -> HealthCheckResult:
        if self.token == _UNCONFIGURED_TOKEN:
            return HealthCheckResult(
                ServiceStatus.UNCONFIGURED,
                "GIT_HUB_TOKEN not configured — GitHub integration disabled",
            )
        if self.gh is None:
            return HealthCheckResult(
                ServiceStatus.ERROR,
                "Failed to initialize GitHub client",
            )
        return HealthCheckResult(
            ServiceStatus.OK,
            f"Configured (org: {self.org_name})",
        )

    # --- GitHub API helpers ---
    async def get_user(self) -> str | None:
        if not self.gh:
            logger.error("GitHub client not initialized.")
            return None
        try:
            user = await self.gh.getitem("/user")
            if not isinstance(user, dict):
                return None
            login = user.get("login")
            if isinstance(login, str):
                return login
            return None
        except Exception as e:
            logger.error(f"Failed to fetch user: {e}")
            return None

    async def get_org_commit_stats(
        self,
        since_date: datetime | None = None,
        only_contributed: bool = False,
    ) -> list[RepoCommitStat] | None:
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

    @staticmethod
    def _parse_pr_url(pr_url: str) -> tuple[str, str, int]:
        """
        Parse a GitHub PR URL and return (owner, repo, number).
        Accepts forms like:
          https://github.com/owner/repo/pull/123
          https://github.com/owner/repo/pull/123/files
          https://github.com/owner/repo/pull/123/commits
        """
        try:
            path = urlparse(pr_url).path.strip("/")
            # path => owner/repo/pull/123[/...]
            m = re_match(r"^([^/]+)/([^/]+)/pull/(\d+)", path)
            if not m:
                raise ValueError("Not a valid GitHub PR URL.")
            owner, repo, number_str = m.groups()
            return owner, repo, int(number_str)
        except Exception as e:
            raise ValueError(f"Failed to parse PR URL '{pr_url}': {e}")

    async def has_user_approved_pr(
        self,
        pr_url: str | None = None,
    ) -> bool | None:
        """
        Return True if the (latest) review by 'user_login' on the given PR is APPROVED.
        Return False if they haven't approved (or later changed to CHANGES_REQUESTED/DISMISSED).
        Return None on API/init errors.

        If user_login is None, uses the authenticated user (self.get_user()).
        """
        if not self.gh:
            logger.error("GitHub client not initialized.")
            return None

        if not pr_url:
            return None

        # Determine which user to check
        user_login = await self.get_user()
        if not user_login:
            logger.error("Could not resolve current GitHub user.")
            return None

        try:
            owner, repo, number = self._parse_pr_url(pr_url)
        except ValueError as e:
            logger.error(str(e))
            return None

        try:
            # Iterate all reviews (handles pagination)
            reviews = []
            async for review in self.gh.getiter(
                f"/repos/{owner}/{repo}/pulls/{number}/reviews"
            ):
                # Safety: some reviews can be from bots or deleted users
                u = (review.get("user") or {}).get("login") or ""
                if u.lower() == user_login.lower():
                    reviews.append(review)

            if not reviews:
                # No reviews from that user at all
                return False

            # Consider only the *latest* review from that user
            # (Only the most recent state counts)
            latest = max(
                reviews,
                key=lambda r: r.get("submitted_at")
                or r.get("commit_id")
                or "",  # fallback tie-breaker
            )
            state = (latest.get("state") or "").upper()
            # Possible values: APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED, PENDING
            return state == "APPROVED"

        except Exception as e:
            logger.error(f"Failed to fetch reviews for {owner}/{repo}#{number}: {e}")
            return None

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
    def get_commit_stats_summary(commit_stats: list[RepoCommitStat] | None) -> str:
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
    def print_commit_stats(commit_stats: list[RepoCommitStat] | None) -> None:
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

    async def update_status_if_task_reviewed(self, code_review: list[Task]) -> None:
        for task in code_review:
            has_been_reviewed = await self.has_user_approved_pr(task.github)
            if has_been_reviewed:
                task.status = Status.DONE

    async def __aenter__(self) -> "GithubService":
        self.client = httpx.AsyncClient()
        try:
            self.gh = GitHubAPI(self.client, requester="taskjournal", oauth_token=self.token)
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            self.gh = None
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Gracefully close the underlying httpx client."""
        if self.client:
            await self.client.aclose()
