from typing import Any

from taskjournal.models.github import PullRequest, RepoCommitStat


def map_pending_pr(item: dict[str, Any]) -> PullRequest:
    repo_url: str = item.get("repository_url", "")
    repo = repo_url.rsplit("/", 1)[-1] if repo_url else "unknown"
    return PullRequest(
        number=item["number"],
        title=item["title"],
        repo=repo,
        url=item["html_url"],
        author=(item.get("user") or {}).get("login", "unknown"),
    )


def review_is_approved(
    pr: dict[str, Any], reviews: list[dict[str, Any]], user_login: str
) -> bool:
    if pr.get("merged"):
        return True
    own_reviews = [
        review
        for review in reviews
        if ((review.get("user") or {}).get("login") or "").lower() == user_login.lower()
    ]
    if not own_reviews:
        return False
    latest = max(own_reviews, key=lambda review: review.get("submitted_at") or "")
    if (latest.get("state") or "").upper() != "APPROVED":
        return False
    head_sha = (pr.get("head") or {}).get("sha")
    review_commit_sha = latest.get("commit_id")
    return not (head_sha and review_commit_sha and head_sha != review_commit_sha)


def commit_stat(repo: str, user_count: int, total_count: int) -> RepoCommitStat:
    return RepoCommitStat(
        repo=repo,
        your_commits=user_count,
        total_commits=total_count,
        percentage=round((user_count / total_count) * 100, 2),
    )
