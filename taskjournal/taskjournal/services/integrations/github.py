from datetime import datetime, timedelta
from re import match as re_match
from urllib.parse import urlparse

from httpx import AsyncClient
from gidgethub.httpx import GitHubAPI

from taskjournal.models.github import PullRequest, RepoCommitStat
from taskjournal.models.task import Status, Task
from taskjournal.services.base import BaseService, HealthCheckResult, ServiceStatus
from taskjournal.services.integrations.github_gateway import GitHubGateway
from taskjournal.services.integrations.github_mapping import commit_stat, map_pending_pr, review_is_approved
from taskjournal.services.logger import logger

_UNCONFIGURED_TOKEN = "your-github-token"


class GithubService(BaseService):
    """Async GitHub service using gidgethub + httpx."""

    def __init__(
        self,
        token: str,
        org_name: str,
        gateway: GitHubGateway | None = None,
    ) -> None:
        self.token = token
        self.org_name = org_name
        self.gateway = gateway if gateway is not None else GitHubGateway(token)

    @property
    def client(self) -> AsyncClient | None:
        return self.gateway.client

    @client.setter
    def client(self, value: AsyncClient | None) -> None:
        self.gateway.client = value

    @property
    def gh(self) -> GitHubAPI | None:
        return self.gateway.gh

    @gh.setter
    def gh(self, value: GitHubAPI | None) -> None:
        self.gateway.gh = value

    @property
    def name(self) -> str:
        return "GitHub"

    def health_check(self) -> HealthCheckResult:
        if self.token == _UNCONFIGURED_TOKEN:
            return HealthCheckResult(
                ServiceStatus.UNCONFIGURED,
                "GIT_HUB_TOKEN not configured — GitHub integration disabled",
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
            user = await self.gateway.getitem("/user")
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
        repo_count = 0

        try:
            async for repo in self.gateway.getiter(f"/orgs/{self.org_name}/repos?type=all&per_page=100"):
                repo_count += 1
                repo_name = repo["name"]

                try:
                    # Count user commits
                    user_count = await self.gateway.count(
                        f"/repos/{self.org_name}/{repo_name}/commits?author={username}&since={since_str}"
                    )

                    if only_contributed and user_count == 0:
                        continue

                    # Count all commits
                    total_count = await self.gateway.count(
                        f"/repos/{self.org_name}/{repo_name}/commits?since={since_str}"
                    )

                    if total_count == 0:
                        continue

                    commit_stats.append(commit_stat(repo_name, user_count, total_count))
                except Exception as e:
                    logger.warning(f"Skipping repo '{repo_name}' due to error: {e}")

        except Exception as e:
            logger.error(f"Failed to fetch repos for org '{self.org_name}': {e}")
            return None

        logger.debug(f"Scanned {repo_count} repos in org '{self.org_name}'")
        if not commit_stats:
            logger.info(f"No contributions found across {repo_count} repos.")
            if repo_count <= 1:
                logger.warning(
                    "Only 1 repo visible — GitHub token may be missing 'repo' scope. "
                    "Regenerate at https://github.com/settings/tokens with 'repo' checked."
                )
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
        Return True if the PR has already been merged, or if the (latest)
        review by the current user is APPROVED and still matches the PR's
        current head commit.
        Return False if it isn't merged and hasn't been (freshly) approved.
        Return None on API/init errors.
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
            pr = await self.gateway.getitem(f"/repos/{owner}/{repo}/pulls/{number}")
            if pr.get("merged"):
                # A merged PR has already gone through its review/merge
                # process, regardless of whether this user personally
                # approved it.
                return True

            # Iterate all reviews (handles pagination)
            reviews = []
            async for review in self.gateway.getiter(
                f"/repos/{owner}/{repo}/pulls/{number}/reviews"
            ):
                reviews.append(review)

            return review_is_approved(pr, reviews, user_login)

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

    async def get_contributions_last_quarter(self) -> str:
        last_quarter = datetime.now() - timedelta(days=91)
        stats = await self.get_org_commit_stats(
            since_date=last_quarter, only_contributed=True
        )
        return self.get_commit_stats_summary(stats)

    async def get_contributions_last_year(self) -> str:
        last_year = datetime.now() - timedelta(days=365)
        stats = await self.get_org_commit_stats(
            since_date=last_year, only_contributed=True
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

    async def get_prs_pending_review(self) -> list[PullRequest]:
        if not self.gh:
            logger.error("GitHub client not initialized.")
            return []
        try:
            query = f"is:pr+is:open+org:{self.org_name}+review-requested:@me"
            data = await self.gateway.getitem(f"/search/issues?q={query}")
            return [map_pending_pr(item) for item in data.get("items", [])]
        except Exception as e:
            logger.error(f"Failed to fetch PRs pending review: {e}")
            return []

    async def update_status_if_task_reviewed(self, code_review: list[Task]) -> None:
        for task in code_review:
            has_been_reviewed = await self.has_user_approved_pr(task.github)
            if has_been_reviewed:
                task.status = Status.DONE

    async def __aenter__(self) -> "GithubService":
        await self.gateway.open()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Gracefully close the underlying httpx client."""
        await self.gateway.close()
