from datetime import datetime
from typing import Any
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from unittest.mock import AsyncMock, patch

from pytest import LogCaptureFixture, mark, raises
from pytest_mock import MockerFixture

from taskjournal.models.github import RepoCommitStat
from taskjournal.models.task import Task, Status
from taskjournal.services.github import GithubService


def make_fake_repos(names: Sequence[str]) -> list[dict[str, str]]:
    return [{"name": n} for n in names]


def make_fake_getiter(
    repos: Sequence[Mapping[str, str]],
    commits_map: Mapping[str, Mapping[str, int]],
) -> Callable[[str], AsyncIterator[dict[str, Any]]]:
    """
    repos: list of repo dicts
    commits_map: dict {repo_name: {"user": int, "total": int}}
    """

    async def fake_getiter(url: str) -> AsyncIterator[dict[str, Any]]:
        if url.endswith("/repos"):
            for r in repos:
                yield dict(r)
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


class TestGithub:

    @mark.asyncio
    async def test_aenter_creates_new_client_and_returns_self(
        self, mocker: MockerFixture
    ) -> None:
        service = GithubService(token="t", org_name="o")
        old_client = service.client

        result = await service.__aenter__()

        assert result is service
        assert service.client is not old_client
        assert service.gh is not None

    @mark.asyncio
    async def test_aexit_closes_client(self, mocker: MockerFixture) -> None:
        service = GithubService(token="t", org_name="o")
        close_spy = mocker.patch.object(service, "close", new_callable=AsyncMock)

        await service.__aexit__(None, None, None)

        close_spy.assert_awaited_once()

    @mark.asyncio
    async def test_close_closes_httpx_client(self, mocker: MockerFixture) -> None:
        # given
        class FakeClient:
            async def aclose(self) -> None:
                return None

        client = FakeClient()
        aclose_spy = mocker.spy(client, "aclose")
        service = GithubService(token="t", org_name="o")
        service.client = client  # type: ignore[assignment]

        # when
        await service.close()

        # then
        assert aclose_spy.call_count == 1

    @mark.asyncio
    async def test_close_skips_when_client_is_none(
        self, github_service: GithubService
    ) -> None:
        # when
        github_service.client = None

        # then
        await github_service.close()

    @mark.asyncio
    async def test_get_user_returns_login(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        assert github_service.gh is not None
        github_service.gh.getitem = mocker.AsyncMock(return_value={"login": "foo"})

        # when
        result = await github_service.get_user()

        # then
        assert result == "foo"

    @mark.asyncio
    async def test_get_user_returns_none_when_no_gh(
        self,
        github_service: GithubService,
    ) -> None:
        # given
        github_service.gh = None

        # when
        result = await github_service.get_user()

        # then
        assert result is None

    @mark.asyncio
    async def test_get_user_logs_error(
        self,
        github_service: GithubService,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        assert github_service.gh is not None
        github_service.gh.getitem = mocker.AsyncMock(side_effect=Exception("boom"))

        # when
        result = await github_service.get_user()

        # then
        assert result is None
        assert "Failed to fetch user" in caplog.text

    @mark.asyncio
    async def test_only_contributed_true_returns_only_user_repos(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value="testuser")
        # when
        repos = make_fake_repos(["repo1", "repo2", "repo3"])
        commits_map = {
            "repo1": {"user": 5, "total": 10},
            "repo2": {"user": 0, "total": 10},
            "repo3": {"user": 2, "total": 3},
        }
        assert github_service.gh is not None
        github_service.gh.getiter = make_fake_getiter(repos, commits_map)

        results = await github_service.get_org_commit_stats(
            since_date=datetime(2024, 1, 1), only_contributed=True
        )

        # then
        assert results is not None
        assert {r.repo for r in results} == {"repo1", "repo3"}

    @mark.asyncio
    async def test_only_contributed_false_returns_all_with_total_commits(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value="testuser")
        # when
        repos = make_fake_repos(["repo1", "repo2", "repo3"])
        commits_map = {
            "repo1": {"user": 0, "total": 10},
            "repo2": {"user": 3, "total": 4},
            "repo3": {"user": 0, "total": 0},  # excluded
        }
        assert github_service.gh is not None
        github_service.gh.getiter = make_fake_getiter(repos, commits_map)

        results = await github_service.get_org_commit_stats(
            since_date=datetime(2024, 1, 1), only_contributed=False
        )

        # then
        assert results is not None
        assert {r.repo for r in results} == {"repo1", "repo2"}

    @mark.asyncio
    async def test_returns_none_if_no_valid_repos(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value="testuser")
        # when
        repos = make_fake_repos(["repo1", "repo2"])
        commits_map = {
            "repo1": {"user": 0, "total": 0},
            "repo2": {"user": 0, "total": 0},
        }
        assert github_service.gh is not None
        github_service.gh.getiter = make_fake_getiter(repos, commits_map)

        result = await github_service.get_org_commit_stats(
            since_date=datetime(2024, 1, 1), only_contributed=False
        )

        # then
        assert result is None

    @mark.asyncio
    async def test_results_are_sorted_by_percentage_desc(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value="testuser")
        # when
        repos = make_fake_repos(["repo1", "repo2", "repo3"])
        commits_map = {
            "repo1": {"user": 5, "total": 10},  # 50%
            "repo2": {"user": 1, "total": 4},  # 25%
            "repo3": {"user": 3, "total": 4},  # 75%
        }
        assert github_service.gh is not None
        github_service.gh.getiter = make_fake_getiter(repos, commits_map)

        results = await github_service.get_org_commit_stats(
            since_date=datetime(2024, 1, 1), only_contributed=False
        )

        # then
        assert results is not None
        assert [r.repo for r in results] == ["repo3", "repo1", "repo2"]

    @mark.asyncio
    async def test_default_since_date_is_jan_1_current_year(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value="testuser")
        # when
        repos = make_fake_repos(["repo"])
        commits_map = {"repo": {"user": 1, "total": 2}}
        assert github_service.gh is not None
        github_service.gh.getiter = make_fake_getiter(repos, commits_map)

        with patch("taskjournal.services.github.datetime") as mock_dt:
            mock_dt.today.return_value = datetime(2025, 8, 16, 12, 0, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            results = await github_service.get_org_commit_stats(
                since_date=None, only_contributed=False
            )

        # then
        assert results is not None
        assert results[0].total_commits == 2

    @mark.asyncio
    async def test_repo_level_exception_is_skipped(
        self,
        github_service: GithubService,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value="testuser")
        # when
        repos = make_fake_repos(["bad", "good"])

        async def fake_getiter(url: str) -> AsyncIterator[dict[str, Any]]:
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

        assert github_service.gh is not None
        github_service.gh.getiter = fake_getiter

        results = await github_service.get_org_commit_stats(
            since_date=datetime(2024, 1, 1), only_contributed=False
        )

        # then
        assert results is not None
        assert [r.repo for r in results] == ["good"]
        assert "Skipping repo 'bad' due to error" in caplog.text

    @mark.asyncio
    async def test_get_org_commit_stats_returns_none_when_no_gh(
        self,
        github_service: GithubService,
    ) -> None:
        # given
        github_service.gh = None

        # when
        result = await github_service.get_org_commit_stats(
            since_date=datetime(2024, 1, 1)
        )

        # then
        assert result is None

    @mark.asyncio
    async def test_get_org_commit_stats_returns_none_when_user_none(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value=None)

        # when
        result = await github_service.get_org_commit_stats(
            since_date=datetime(2024, 1, 1)
        )

        # then
        assert result is None

    @mark.asyncio
    async def test_get_org_commit_stats_returns_none_on_repo_fetch_failure(
        self,
        github_service: GithubService,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value="testuser")

        async def bad_getiter(_url: str) -> AsyncIterator[dict[str, Any]]:
            raise Exception("repo fetch fail")
            yield  # async generator marker

        assert github_service.gh is not None
        github_service.gh.getiter = bad_getiter

        # when
        result = await github_service.get_org_commit_stats(
            since_date=datetime(2024, 1, 1)
        )

        # then
        assert result is None
        assert "Failed to fetch repos" in caplog.text

    def test_get_commit_stats_summary_string_format(self) -> None:
        # given
        stats = [
            RepoCommitStat(repo="r1", your_commits=1, total_commits=2, percentage=50.0),
            RepoCommitStat(
                repo="r2", your_commits=3, total_commits=3, percentage=100.0
            ),
        ]

        # when
        summary = GithubService.get_commit_stats_summary(stats)

        # then
        assert "r1: 1/2 commits (50.0%)" in summary
        assert "r2: 3/3 commits (100.0%)" in summary
        assert "Your commits: 4" in summary
        assert "Org total commits: 5" in summary
        assert "Your overall contribution: 80.0%" in summary

    def test_get_commit_stats_summary_handles_empty(self) -> None:
        # when
        result = GithubService.get_commit_stats_summary(None)

        # then
        assert result == "No commit stats to display."

    @mark.asyncio
    async def test_get_contributions_last_6_months_calls_summary(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        fake_stats = [
            RepoCommitStat(repo="a", your_commits=2, total_commits=4, percentage=50.0)
        ]
        mocker.patch.object(
            GithubService, "get_org_commit_stats", return_value=fake_stats
        )
        # when
        mock_summary = mocker.spy(GithubService, "get_commit_stats_summary")

        out = await github_service.get_contributions_last_6_months()

        # then
        assert mock_summary.call_count == 1
        assert "Overall Contribution Summary" in out

    @mark.asyncio
    async def test_get_contributions_last_month_calls_summary(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        fake_stats = [
            RepoCommitStat(repo="b", your_commits=1, total_commits=2, percentage=50.0)
        ]
        mocker.patch.object(
            GithubService, "get_org_commit_stats", return_value=fake_stats
        )
        # when
        mock_summary = mocker.spy(GithubService, "get_commit_stats_summary")

        out = await github_service.get_contributions_last_month()

        # then
        assert mock_summary.call_count == 1
        assert "Overall Contribution Summary" in out

    @mark.asyncio
    async def test_aenter_handles_github_client_init_failure(
        self, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch(
            "taskjournal.services.github.GitHubAPI", side_effect=Exception("boom")
        )
        logger_mock = mocker.patch("taskjournal.services.github.logger")

        # when
        service = GithubService(token="t", org_name="o")
        await service.__aenter__()

        # then
        assert service.gh is None
        logger_mock.error.assert_called_once()
        await service.close()

    def test_parse_pr_url_success_and_invalid(self) -> None:
        # given
        pull_request_url = "https://github.com/acme/repo/pull/123/files"
        invalid_url = "https://github.com/acme/repo/issues/1"

        # when
        owner, repo, number = GithubService._parse_pr_url(pull_request_url)

        # then
        assert (owner, repo, number) == ("acme", "repo", 123)
        with raises(ValueError):
            GithubService._parse_pr_url(invalid_url)

    @mark.asyncio
    async def test_has_user_approved_pr_returns_none_on_uninitialized_gh(
        self,
        github_service: GithubService,
    ) -> None:
        # given
        github_service.gh = None

        # when
        result = await github_service.has_user_approved_pr(
            "https://github.com/a/b/pull/1"
        )

        # then
        assert result is None

    @mark.asyncio
    async def test_has_user_approved_pr_returns_none_when_no_pr_url(
        self,
        github_service: GithubService,
    ) -> None:
        # when
        result = await github_service.has_user_approved_pr(None)

        # then
        assert result is None

    @mark.asyncio
    async def test_has_user_approved_pr_returns_none_when_user_missing(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value=None)

        # when
        result = await github_service.has_user_approved_pr(
            "https://github.com/a/b/pull/1"
        )

        # then
        assert result is None

    @mark.asyncio
    async def test_has_user_approved_pr_returns_none_on_bad_pr_url(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value="me")

        # when
        result = await github_service.has_user_approved_pr("invalid-url")

        # then
        assert result is None

    @mark.asyncio
    async def test_has_user_approved_pr_returns_false_without_reviews(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value="me")

        async def fake_getiter(_url: str) -> AsyncIterator[dict[str, Any]]:
            if False:
                yield {}

        assert github_service.gh is not None
        github_service.gh.getiter = fake_getiter

        # when
        result = await github_service.has_user_approved_pr(
            "https://github.com/acme/r/pull/99"
        )

        # then
        assert result is False

    @mark.asyncio
    async def test_has_user_approved_pr_uses_latest_state(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value="me")

        async def fake_getiter(_url: str) -> AsyncIterator[dict[str, Any]]:
            yield {
                "user": {"login": "me"},
                "state": "APPROVED",
                "submitted_at": "2025-01-01T10:00:00Z",
            }
            yield {
                "user": {"login": "me"},
                "state": "CHANGES_REQUESTED",
                "submitted_at": "2025-01-02T10:00:00Z",
            }

        assert github_service.gh is not None
        github_service.gh.getiter = fake_getiter

        # when
        result = await github_service.has_user_approved_pr(
            "https://github.com/acme/r/pull/99"
        )

        # then
        assert result is False

    @mark.asyncio
    async def test_has_user_approved_pr_returns_true_for_latest_approved(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value="me")

        async def fake_getiter(_url: str) -> AsyncIterator[dict[str, Any]]:
            yield {"user": {"login": "other"}, "state": "APPROVED"}
            yield {
                "user": {"login": "ME"},
                "state": "APPROVED",
                "submitted_at": "2025-01-02T10:00:00Z",
            }

        assert github_service.gh is not None
        github_service.gh.getiter = fake_getiter

        # when
        result = await github_service.has_user_approved_pr(
            "https://github.com/acme/r/pull/99"
        )

        # then
        assert result is True

    @mark.asyncio
    async def test_has_user_approved_pr_returns_none_on_review_fetch_error(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(github_service, "get_user", return_value="me")

        async def bad_getiter(_url: str) -> AsyncIterator[dict[str, Any]]:
            raise Exception("boom")
            yield

        assert github_service.gh is not None
        github_service.gh.getiter = bad_getiter

        # when
        result = await github_service.has_user_approved_pr(
            "https://github.com/acme/r/pull/99"
        )

        # then
        assert result is None

    def test_get_commit_stats_summary_handles_zero_totals(self) -> None:
        # given
        stats = [
            RepoCommitStat(repo="r1", your_commits=0, total_commits=0, percentage=0)
        ]

        # when
        summary = GithubService.get_commit_stats_summary(stats)

        # then
        assert "Your overall contribution: 0%" in summary

    def test_print_commit_stats_empty_and_non_empty(
        self, mocker: MockerFixture
    ) -> None:
        # given
        logger = mocker.patch("taskjournal.services.github.logger")
        # when
        GithubService.print_commit_stats(None)
        # then
        logger.info.assert_called_once_with("No commit stats to display.")

        logger.reset_mock()
        GithubService.print_commit_stats(
            [
                RepoCommitStat(
                    repo="r1", your_commits=1, total_commits=2, percentage=50.0
                )
            ]
        )
        assert logger.info.call_count >= 4

    @mark.asyncio
    async def test_update_status_if_task_reviewed(
        self, github_service: GithubService, mocker: MockerFixture
    ) -> None:
        # given
        mocker.patch.object(
            github_service, "has_user_approved_pr", side_effect=[True, False, None]
        )
        # when
        tasks = [
            Task(id="1", description="a", status=Status.TODO, github="u1"),
            Task(id="2", description="b", status=Status.TODO, github="u2"),
            Task(id="3", description="c", status=Status.TODO, github="u3"),
        ]

        await github_service.update_status_if_task_reviewed(tasks)

        # then
        assert tasks[0].status == Status.DONE
        assert tasks[1].status == Status.TODO
        assert tasks[2].status == Status.TODO
