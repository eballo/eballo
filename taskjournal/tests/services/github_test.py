from datetime import datetime
from unittest.mock import patch

import pytest

from taskjournal.models.github import RepoCommitStat
from taskjournal.services.github import GithubService


# ============================================================
# Helpers
# ============================================================


def make_fake_repos(names):
    return [{"name": n} for n in names]


def make_fake_getiter(repos, commits_map):
    """
    repos: list of repo dicts
    commits_map: dict {repo_name: {"user": int, "total": int}}
    """

    async def fake_getiter(url):
        if url.endswith("/repos"):
            for r in repos:
                yield r
        else:
            for repo, stats in commits_map.items():
                if repo in url:
                    if "author=" in url:
                        for _ in range(stats["user"]):
                            yield {}
                    else:
                        for _ in range(stats["total"]):
                            yield {}

    return fake_getiter


# ============================================================
# Lifecycle
# ============================================================


@pytest.mark.asyncio
async def test_close_closes_httpx_client(mocker):
    # Given a FakeClient to track aclose
    closed = False

    class FakeClient:
        async def aclose(self):
            nonlocal closed
            closed = True

    mocker.patch("httpx.AsyncClient", return_value=FakeClient())
    service = GithubService(token="t", org_name="o")

    # When calling close
    await service.close()

    # Then aclose was called
    assert closed


# ============================================================
# get_user
# ============================================================


@pytest.mark.asyncio
async def test_get_user_returns_login(mocker):
    # Given GH API with a /user response
    service = GithubService()
    service.gh.getitem = mocker.AsyncMock(return_value={"login": "foo"})

    # When
    result = await service.get_user()

    # Then
    assert result == "foo"


@pytest.mark.asyncio
async def test_get_user_returns_none_when_no_gh():
    # Given uninitialized service
    service = GithubService()
    service.gh = None

    # When
    result = await service.get_user()

    # Then
    assert result is None


@pytest.mark.asyncio
async def test_get_user_logs_error(mocker, caplog):
    # Given GH API raising
    service = GithubService()
    service.gh.getitem = mocker.AsyncMock(side_effect=Exception("boom"))

    # When
    result = await service.get_user()

    # Then
    assert result is None
    assert "Failed to fetch user" in caplog.text


# ============================================================
# get_org_commit_stats
# ============================================================


@pytest.mark.asyncio
async def test_only_contributed_true_returns_only_user_repos(mocker):
    # Given repos with/without commits
    service = GithubService()
    mocker.patch.object(service, "get_user", return_value="testuser")
    repos = make_fake_repos(["repo1", "repo2", "repo3"])
    commits_map = {
        "repo1": {"user": 5, "total": 10},
        "repo2": {"user": 0, "total": 10},
        "repo3": {"user": 2, "total": 3},
    }
    service.gh.getiter = make_fake_getiter(repos, commits_map)

    # When
    results = await service.get_org_commit_stats(
        since_date=datetime(2024, 1, 1), only_contributed=True
    )

    # Then
    assert {r.repo for r in results} == {"repo1", "repo3"}


@pytest.mark.asyncio
async def test_only_contributed_false_returns_all_with_total_commits(mocker):
    # Given repos with commits
    service = GithubService()
    mocker.patch.object(service, "get_user", return_value="testuser")
    repos = make_fake_repos(["repo1", "repo2", "repo3"])
    commits_map = {
        "repo1": {"user": 0, "total": 10},
        "repo2": {"user": 3, "total": 4},
        "repo3": {"user": 0, "total": 0},  # excluded
    }
    service.gh.getiter = make_fake_getiter(repos, commits_map)

    # When
    results = await service.get_org_commit_stats(
        since_date=datetime(2024, 1, 1), only_contributed=False
    )

    # Then
    assert {r.repo for r in results} == {"repo1", "repo2"}


@pytest.mark.asyncio
async def test_returns_none_if_no_valid_repos(mocker):
    # Given repos with no commits
    service = GithubService()
    mocker.patch.object(service, "get_user", return_value="testuser")
    repos = make_fake_repos(["repo1", "repo2"])
    commits_map = {"repo1": {"user": 0, "total": 0}, "repo2": {"user": 0, "total": 0}}
    service.gh.getiter = make_fake_getiter(repos, commits_map)

    # When
    result = await service.get_org_commit_stats(
        since_date=datetime(2024, 1, 1), only_contributed=False
    )

    # Then
    assert result is None


@pytest.mark.asyncio
async def test_results_are_sorted_by_percentage_desc(mocker):
    # Given repos with different stats
    service = GithubService()
    mocker.patch.object(service, "get_user", return_value="testuser")
    repos = make_fake_repos(["repo1", "repo2", "repo3"])
    commits_map = {
        "repo1": {"user": 5, "total": 10},  # 50%
        "repo2": {"user": 1, "total": 4},  # 25%
        "repo3": {"user": 3, "total": 4},  # 75%
    }
    service.gh.getiter = make_fake_getiter(repos, commits_map)

    # When
    results = await service.get_org_commit_stats(
        since_date=datetime(2024, 1, 1), only_contributed=False
    )

    # Then
    assert [r.repo for r in results] == ["repo3", "repo1", "repo2"]


@pytest.mark.asyncio
async def test_default_since_date_is_jan_1_current_year(mocker):
    # Given datetime patched
    service = GithubService()
    mocker.patch.object(service, "get_user", return_value="testuser")
    repos = make_fake_repos(["repo"])
    commits_map = {"repo": {"user": 1, "total": 2}}
    service.gh.getiter = make_fake_getiter(repos, commits_map)

    with patch("taskjournal.services.github.datetime") as mock_dt:
        mock_dt.today.return_value = datetime(2025, 8, 16, 12, 0, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        # When since_date=None
        results = await service.get_org_commit_stats(
            since_date=None, only_contributed=False
        )

    # Then
    assert results[0].total_commits == 2


@pytest.mark.asyncio
async def test_repo_level_exception_is_skipped(mocker, caplog):
    # Given one bad repo
    service = GithubService()
    mocker.patch.object(service, "get_user", return_value="testuser")
    repos = make_fake_repos(["bad", "good"])

    async def fake_getiter(url):
        if url.endswith("/repos"):
            for r in repos:
                yield r
        elif "bad" in url:
            raise Exception("boom")
        elif "good" in url:
            if "author=" in url:
                for _ in range(2):
                    yield {}
            else:
                for _ in range(4):
                    yield {}

    service.gh.getiter = fake_getiter

    # When
    results = await service.get_org_commit_stats(
        since_date=datetime(2024, 1, 1), only_contributed=False
    )

    # Then
    assert [r.repo for r in results] == ["good"]
    assert "Skipping repo 'bad' due to error" in caplog.text


@pytest.mark.asyncio
async def test_get_org_commit_stats_returns_none_when_no_gh():
    # Given gh=None
    service = GithubService()
    service.gh = None

    # When
    result = await service.get_org_commit_stats(since_date=datetime(2024, 1, 1))

    # Then
    assert result is None


@pytest.mark.asyncio
async def test_get_org_commit_stats_returns_none_when_user_none(mocker):
    # Given get_user returns None
    service = GithubService()
    mocker.patch.object(service, "get_user", return_value=None)

    # When
    result = await service.get_org_commit_stats(since_date=datetime(2024, 1, 1))

    # Then
    assert result is None


@pytest.mark.asyncio
async def test_get_org_commit_stats_returns_none_on_repo_fetch_failure(mocker, caplog):
    # Given repo listing fails
    service = GithubService()
    mocker.patch.object(service, "get_user", return_value="testuser")

    async def bad_getiter(url):
        raise Exception("repo fetch fail")
        yield  # async generator marker

    service.gh.getiter = bad_getiter

    # When
    result = await service.get_org_commit_stats(since_date=datetime(2024, 1, 1))

    # Then
    assert result is None
    assert "Failed to fetch repos" in caplog.text


# ============================================================
# get_commit_stats_summary
# ============================================================


def test_get_commit_stats_summary_string_format():
    # Given stats
    stats = [
        RepoCommitStat(repo="r1", your_commits=1, total_commits=2, percentage=50.0),
        RepoCommitStat(repo="r2", your_commits=3, total_commits=3, percentage=100.0),
    ]

    # When
    summary = GithubService.get_commit_stats_summary(stats)

    # Then
    assert "r1: 1/2 commits (50.0%)" in summary
    assert "r2: 3/3 commits (100.0%)" in summary
    assert "Your commits: 4" in summary
    assert "Org total commits: 5" in summary
    assert "Your overall contribution: 80.0%" in summary


def test_get_commit_stats_summary_handles_empty():
    # When
    result = GithubService.get_commit_stats_summary(None)

    # Then
    assert result == "No commit stats to display."


# ============================================================
# get_contributions_last_6_months / last_month
# ============================================================


@pytest.mark.asyncio
async def test_get_contributions_last_6_months_calls_summary(mocker):
    # Given fake stats
    service = GithubService()
    fake_stats = [
        RepoCommitStat(repo="a", your_commits=2, total_commits=4, percentage=50.0)
    ]
    mocker.patch.object(GithubService, "get_org_commit_stats", return_value=fake_stats)
    mock_summary = mocker.spy(GithubService, "get_commit_stats_summary")

    # When
    out = await service.get_contributions_last_6_months()

    # Then
    assert mock_summary.call_count == 1
    assert "Overall Contribution Summary" in out


@pytest.mark.asyncio
async def test_get_contributions_last_month_calls_summary(mocker):
    # Given fake stats
    service = GithubService()
    fake_stats = [
        RepoCommitStat(repo="b", your_commits=1, total_commits=2, percentage=50.0)
    ]
    mocker.patch.object(GithubService, "get_org_commit_stats", return_value=fake_stats)
    mock_summary = mocker.spy(GithubService, "get_commit_stats_summary")

    # When
    out = await service.get_contributions_last_month()

    # Then
    assert mock_summary.call_count == 1
    assert "Overall Contribution Summary" in out
