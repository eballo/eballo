from datetime import datetime, timedelta
from typing import Any
from collections.abc import AsyncIterator

from freezegun import freeze_time
from pytest import LogCaptureFixture, mark
from pytest_mock import MockerFixture

from taskjournal.models.github import RepoCommitStat
from taskjournal.services.base import ServiceStatus
from taskjournal.services.integrations.github import GithubService


def test_name_and_health_check_when_configured(github_service: GithubService) -> None:
    assert github_service.name == "GitHub"
    result = github_service.health_check()
    assert result.status == ServiceStatus.OK
    assert result.message == "Configured (org: test-org)"


def test_health_check_when_token_is_placeholder() -> None:
    result = GithubService(
        token="your-github-token", org_name="test-org"
    ).health_check()
    assert result.status == ServiceStatus.UNCONFIGURED
    assert "GIT_HUB_TOKEN not configured" in result.message


@mark.asyncio
@mark.parametrize("response", [None, [], {"login": None}, {"login": 42}, {}])
async def test_get_user_ignores_invalid_api_responses(
    github_service: GithubService, mocker: MockerFixture, response: Any
) -> None:
    getitem = mocker.patch.object(
        github_service.gateway, "getitem", return_value=response
    )

    assert await github_service.get_user() is None
    getitem.assert_awaited_once_with("/user")


@mark.asyncio
@mark.parametrize("repo_count, warns", [(0, True), (1, True), (2, False)])
async def test_no_commit_stats_warns_about_scope_only_for_at_most_one_repo(
    github_service: GithubService,
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
    repo_count: int,
    warns: bool,
) -> None:
    mocker.patch.object(github_service, "get_user", return_value="me")

    async def repos(_url: str) -> AsyncIterator[dict[str, str]]:
        for index in range(repo_count):
            yield {"name": f"repo-{index}"}

    getiter = mocker.patch.object(github_service.gateway, "getiter", side_effect=repos)
    count = mocker.patch.object(github_service.gateway, "count", return_value=0)

    result = await github_service.get_org_commit_stats(since_date=datetime(2026, 1, 1))

    assert result is None
    getiter.assert_called_once_with("/orgs/test-org/repos?type=all&per_page=100")
    assert count.await_count == repo_count * 2
    assert ("token may be missing 'repo' scope" in caplog.text) is warns


@mark.asyncio
@mark.parametrize(
    "method, days",
    [("get_contributions_last_quarter", 91), ("get_contributions_last_year", 365)],
)
async def test_contribution_windows_forward_dates_and_format_stats(
    github_service: GithubService, mocker: MockerFixture, method: str, days: int
) -> None:
    stats = [
        RepoCommitStat(repo="repo", your_commits=2, total_commits=4, percentage=50.0)
    ]
    get_stats = mocker.patch.object(
        github_service, "get_org_commit_stats", return_value=stats
    )

    with freeze_time("2026-09-23 13:27:00"):
        summary = await getattr(github_service, method)()

    get_stats.assert_awaited_once_with(
        since_date=datetime(2026, 9, 23, 13, 27) - timedelta(days=days),
        only_contributed=True,
    )
    assert "repo: 2/4 commits (50.0%)" in summary
    assert "Your overall contribution: 50.0%" in summary


@mark.asyncio
async def test_pending_reviews_without_client_returns_empty(
    github_service: GithubService, mocker: MockerFixture
) -> None:
    getitem = mocker.patch.object(github_service.gateway, "getitem")
    github_service.gh = None

    assert await github_service.get_prs_pending_review() == []
    getitem.assert_not_awaited()


@mark.asyncio
async def test_pending_reviews_map_search_results(
    github_service: GithubService, mocker: MockerFixture
) -> None:
    getitem = mocker.patch.object(
        github_service.gateway,
        "getitem",
        return_value={
            "items": [
                {
                    "number": 17,
                    "title": "Review me",
                    "html_url": "https://github.com/test-org/repo/pull/17",
                    "repository_url": "https://api.github.com/repos/test-org/repo",
                    "user": {"login": "author"},
                }
            ]
        },
    )

    prs = await github_service.get_prs_pending_review()

    getitem.assert_awaited_once_with(
        "/search/issues?q=is:pr+is:open+org:test-org+review-requested:@me"
    )
    assert len(prs) == 1
    assert (prs[0].number, prs[0].title, prs[0].repo, prs[0].author) == (
        17,
        "Review me",
        "repo",
        "author",
    )
    assert prs[0].url == "https://github.com/test-org/repo/pull/17"


@mark.asyncio
async def test_pending_reviews_with_no_items_returns_empty(
    github_service: GithubService, mocker: MockerFixture
) -> None:
    mocker.patch.object(github_service.gateway, "getitem", return_value={})
    assert await github_service.get_prs_pending_review() == []


@mark.asyncio
@mark.parametrize(
    "response", [RuntimeError("API unavailable"), {"items": [{"number": 17}]}]
)
async def test_pending_reviews_handles_fetch_or_mapping_errors(
    github_service: GithubService,
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
    response: Any,
) -> None:
    if isinstance(response, Exception):
        mocker.patch.object(github_service.gateway, "getitem", side_effect=response)
    else:
        mocker.patch.object(github_service.gateway, "getitem", return_value=response)

    assert await github_service.get_prs_pending_review() == []
    assert "Failed to fetch PRs pending review" in caplog.text
