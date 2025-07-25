from github import Github

from taskjournal.config import GIT_HUB_TOKEN
from taskjournal.services.logger import logger


class GithubService:

    def __init__(self):
        self.github_client = Github(GIT_HUB_TOKEN)

    def get_user(self):
        return self.github_client.get_user()

    def get_contributed_repos(self):
        user = self.get_user()
        repos = user.get_repos()

        contributed = []

        for repo in repos:
            try:
                commits = repo.get_commits(author=user)
                if commits.totalCount > 0:
                    contributed.append(repo.full_name)
            except:
                pass  # Handle permission errors etc.

        logger.info("Repos you've committed to:")
        for r in contributed:
            logger.info(r)

    def get_org_commit_stats(self, org_name="kidoodleDEV", since_date=None):
        """
        Get total commits and user commits for all repos in an org since a given date.

        :param org_name: Name of the GitHub organization
        :param since_date: A datetime object (e.g., datetime(2024, 1, 1))
        """
        user = self.get_user()
        username = user.login

        try:
            org = self.github_client.get_organization(org_name)
        except Exception as e:
            logger.error(f"Failed to fetch organization '{org_name}': {e}")
            return

        if since_date is None:
            since_date = datetime(
                datetime.today().year, 1, 1
            )  # Default: start of the year

        logger.info(
            f"Gathering commit stats since {since_date.date()} for user '{username}' in org '{org_name}'..."
        )

        commit_stats = []

        for repo in org.get_repos():
            try:
                total_commits = repo.get_commits(since=since_date).totalCount
                user_commits = repo.get_commits(
                    author=username, since=since_date
                ).totalCount

                if total_commits == 0:
                    continue

                percentage = round((user_commits / total_commits) * 100, 2)

                commit_stats.append(
                    {
                        "repo": repo.name,
                        "your_commits": user_commits,
                        "total_commits": total_commits,
                        "percentage": percentage,
                    }
                )

            except Exception as e:
                logger.warning(f"Skipping repo '{repo.name}' due to error: {e}")

        commit_stats.sort(key=lambda r: r["percentage"], reverse=True)

        for stat in commit_stats:
            logger.info(
                f"{stat['repo']}: {stat['your_commits']}/{stat['total_commits']} commits "
                f"({stat['percentage']}%)"
            )

        total_user_commits = sum(r["your_commits"] for r in commit_stats)
        total_all_commits = sum(r["total_commits"] for r in commit_stats)
        overall_percentage = (
            round((total_user_commits / total_all_commits) * 100, 2)
            if total_all_commits
            else 0
        )

        logger.info("\n📊 Overall Contribution Summary:")
        logger.info(f"   Your commits: {total_user_commits}")
        logger.info(f"   Org total commits: {total_all_commits}")
        logger.info(f"   Your overall contribution: {overall_percentage}%")
