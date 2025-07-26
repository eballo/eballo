from datetime import datetime

from github import Github

from taskjournal.config import GIT_HUB_TOKEN, GIT_HUB_ORGANIZATION_NAME
from taskjournal.models.github import RepoCommitStat
from taskjournal.services.logger import logger


class GithubService:

    def __init__(self):
        try:
            self.github_client = Github(GIT_HUB_TOKEN)
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")

    def get_user(self):
        return self.github_client.get_user()

    def get_org_commit_stats(
        self,
        org_name: str = GIT_HUB_ORGANIZATION_NAME,
        since_date: datetime | None = None,
        only_contributed: bool = False,
    ) -> list[RepoCommitStat] | None:
        """
        Get commit statistics for each repository in the given organization.

        :param org_name: GitHub organization name
        :param since_date: datetime object (defaults to start of current year)
        :param only_contributed: if True, only include repos where the user contributed
        """
        user = self.get_user()
        username = user.login

        try:
            org = self.github_client.get_organization(org_name)
        except Exception as e:
            logger.error(f"Failed to fetch organization '{org_name}': {e}")
            return None

        if since_date is None:
            since_date = datetime(
                datetime.today().year, 1, 1
            )  # Default: Jan 1 of current year

        logger.info(
            f"Gathering commit stats since {since_date.date()} for user '{username}' in org '{org_name}' "
            f"with only_contributed {only_contributed}..."
        )

        commit_stats = []

        for repo in org.get_repos():
            try:
                user_commits = repo.get_commits(
                    author=username, since=since_date
                ).totalCount

                # Skip if only_contributed is True and user made 0 commits
                if only_contributed and user_commits == 0:
                    continue

                total_commits = repo.get_commits(since=since_date).totalCount
                if total_commits == 0:
                    continue

                percentage = round((user_commits / total_commits) * 100, 2)

                commit_stats.append(
                    RepoCommitStat(
                        repo=repo.name,
                        your_commits=user_commits,
                        total_commits=total_commits,
                        percentage=percentage,
                    )
                )

            except Exception as e:
                logger.warning(f"Skipping repo '{repo.name}' due to error: {e}")

        if not commit_stats:
            logger.info("No contributions found.")
            return None

        commit_stats.sort(key=lambda r: r.percentage, reverse=True)

        return commit_stats

    @staticmethod
    def print_commit_stats(commit_stats: list[RepoCommitStat] | None) -> None:
        """
        Print commit statistics in a formatted table.
        """
        if not commit_stats:
            logger.info("No commit stats to display.")
            return

        for stat in commit_stats:
            logger.info(
                f"{stat.repo}: {stat.your_commits}/{stat.total_commits} commits "
                f"({stat.percentage}%)"
            )

        total_user_commits = sum(repository.your_commits for repository in commit_stats)
        total_all_commits = sum(repository.total_commits for repository in commit_stats)
        overall_percentage = (
            round((total_user_commits / total_all_commits) * 100, 2)
            if total_all_commits
            else 0
        )

        logger.info("\n📊 Overall Contribution Summary:")
        logger.info(f"   Your commits: {total_user_commits}")
        logger.info(f"   Org total commits: {total_all_commits}")
        logger.info(f"   Your overall contribution: {overall_percentage}%")
