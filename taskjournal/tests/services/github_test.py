from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from taskjournal.models.github import RepoCommitStat
from taskjournal.services.github import GithubService


@pytest.fixture
def mocked_github_service():
    with patch("taskjournal.services.github.Github") as MockGithub:
        mock_instance = MockGithub.return_value
        service = GithubService()
        service.github_client = mock_instance
        yield service


def setup_repo_mock(name, user_commit_count, total_commit_count):
    repo = MagicMock()
    repo.name = name
    repo.get_commits.side_effect = [
        MagicMock(totalCount=user_commit_count),
        MagicMock(totalCount=total_commit_count),
    ]
    return repo


def test_only_contributed_true_returns_only_user_repos(mocked_github_service):
    mock_user = MagicMock()
    mock_user.login = "testuser"

    repo1 = setup_repo_mock("repo1", 5, 10)
    repo2 = setup_repo_mock("repo2", 0, 10)
    repo3 = setup_repo_mock("repo3", 2, 3)

    mock_org = MagicMock()
    mock_org.get_repos.return_value = [repo1, repo2, repo3]

    mocked_github_service.get_user = MagicMock(return_value=mock_user)
    mocked_github_service.github_client.get_organization.return_value = mock_org

    results = mocked_github_service.get_org_commit_stats(
        org_name="kidoodleDEV",
        since_date=datetime(2024, 1, 1),
        only_contributed=True,
    )

    assert len(results) == 2
    assert all(isinstance(r, RepoCommitStat) for r in results)
    assert {r.repo for r in results} == {"repo1", "repo3"}


def test_only_contributed_false_returns_all_with_total_commits(mocked_github_service):
    mock_user = MagicMock()
    mock_user.login = "testuser"

    repo1 = setup_repo_mock("repo1", 0, 10)
    repo2 = setup_repo_mock("repo2", 3, 4)
    repo3 = setup_repo_mock("repo3", 0, 0)  # Should be excluded

    mock_org = MagicMock()
    mock_org.get_repos.return_value = [repo1, repo2, repo3]

    mocked_github_service.get_user = MagicMock(return_value=mock_user)
    mocked_github_service.github_client.get_organization.return_value = mock_org

    results = mocked_github_service.get_org_commit_stats(
        org_name="kidoodleDEV",
        since_date=datetime(2024, 1, 1),
        only_contributed=False,
    )

    assert len(results) == 2
    assert {r.repo for r in results} == {"repo1", "repo2"}


def test_returns_none_if_org_fetch_fails(mocked_github_service):
    mocked_github_service.get_user = MagicMock()
    mocked_github_service.github_client.get_organization.side_effect = Exception("fail")

    result = mocked_github_service.get_org_commit_stats(org_name="invalid")
    assert result is None


def test_returns_none_if_no_valid_repos(mocked_github_service):
    mock_user = MagicMock()
    mock_user.login = "testuser"

    repo1 = setup_repo_mock("repo1", 0, 0)
    repo2 = setup_repo_mock("repo2", 0, 0)

    mock_org = MagicMock()
    mock_org.get_repos.return_value = [repo1, repo2]

    mocked_github_service.get_user = MagicMock(return_value=mock_user)
    mocked_github_service.github_client.get_organization.return_value = mock_org

    result = mocked_github_service.get_org_commit_stats(
        org_name="kidoodleDEV",
        since_date=datetime(2024, 1, 1),
        only_contributed=False,
    )

    assert result is None


def test_results_are_sorted_by_percentage_desc(mocked_github_service):
    mock_user = MagicMock()
    mock_user.login = "testuser"

    # percentages: r1=50%, r2=25%, r3=75%
    repo1 = setup_repo_mock("repo1", 5, 10)
    repo2 = setup_repo_mock("repo2", 1, 4)
    repo3 = setup_repo_mock("repo3", 3, 4)

    mock_org = MagicMock()
    mock_org.get_repos.return_value = [repo1, repo2, repo3]

    mocked_github_service.get_user = MagicMock(return_value=mock_user)
    mocked_github_service.github_client.get_organization.return_value = mock_org

    results = mocked_github_service.get_org_commit_stats(
        org_name="kidoodleDEV",
        since_date=datetime(2024, 1, 1),
        only_contributed=False,
    )

    assert [r.repo for r in results] == ["repo3", "repo1", "repo2"]


def test_default_since_date_is_jan_1_current_year(mocked_github_service):
    mock_user = MagicMock()
    mock_user.login = "testuser"

    repo = setup_repo_mock("repo", 1, 2)

    mock_org = MagicMock()
    mock_org.get_repos.return_value = [repo]

    mocked_github_service.get_user = MagicMock(return_value=mock_user)
    mocked_github_service.github_client.get_organization.return_value = mock_org

    # Patch the datetime class inside the module to control today()
    with patch("taskjournal.services.github.datetime") as mock_dt:
        mock_dt.today.return_value = datetime(2025, 8, 16, 12, 0, 0)
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        _ = mocked_github_service.get_org_commit_stats(
            org_name="kidoodleDEV",
            since_date=None,
            only_contributed=False,
        )

        # ensure repo.get_commits was called with since=Jan 1 of current year (2025-01-01)
        # The first call is for user commits, second for total commits.
        kwargs_first = repo.get_commits.call_args_list[0].kwargs
        kwargs_second = repo.get_commits.call_args_list[1].kwargs
        assert kwargs_first["since"].date() == datetime(2025, 1, 1).date()
        assert kwargs_second["since"].date() == datetime(2025, 1, 1).date()


def test_repo_level_exception_is_skipped(mocked_github_service, caplog):
    mock_user = MagicMock()
    mock_user.login = "testuser"

    bad_repo = MagicMock()
    bad_repo.name = "bad"
    bad_repo.get_commits.side_effect = Exception("boom")

    good_repo = setup_repo_mock("good", 2, 4)

    mock_org = MagicMock()
    mock_org.get_repos.return_value = [bad_repo, good_repo]

    mocked_github_service.get_user = MagicMock(return_value=mock_user)
    mocked_github_service.github_client.get_organization.return_value = mock_org

    results = mocked_github_service.get_org_commit_stats(
        org_name="kidoodleDEV",
        since_date=datetime(2024, 1, 1),
        only_contributed=False,
    )

    assert len(results) == 1
    assert results[0].repo == "good"
    assert any(
        "Skipping repo 'bad' due to error" in m for m in caplog.text.splitlines()
    )


def test_print_commit_stats_outputs_expected_lines(mocked_github_service, caplog):
    stats = [
        RepoCommitStat(repo="r1", your_commits=3, total_commits=6, percentage=50.0),
        RepoCommitStat(repo="r2", your_commits=2, total_commits=4, percentage=50.0),
    ]

    GithubService.print_commit_stats(stats)

    assert "r1: 3/6 commits (50.0%)" in caplog.text
    assert "r2: 2/4 commits (50.0%)" in caplog.text
    assert "📊 Overall Contribution Summary:" in caplog.text
    assert "Your commits: 5" in caplog.text
    assert "Org total commits: 10" in caplog.text
    assert "Your overall contribution: 50.0%" in caplog.text


def test_print_commit_stats_handles_empty(mocked_github_service, caplog):
    GithubService.print_commit_stats(None)
    assert "No commit stats to display." in caplog.text


def test_get_commit_stats_summary_string_format(mocked_github_service):
    stats = [
        RepoCommitStat(repo="r1", your_commits=1, total_commits=2, percentage=50.0),
        RepoCommitStat(repo="r2", your_commits=3, total_commits=3, percentage=100.0),
    ]

    summary = GithubService.get_commit_stats_summary(stats)

    assert "r1: 1/2 commits (50.0%)" in summary
    assert "r2: 3/3 commits (100.0%)" in summary
    assert "📊 Overall Contribution Summary:" in summary
    assert "Your commits: 4" in summary
    assert "Org total commits: 5" in summary
    assert "Your overall contribution: 80.0%" in summary


def test_get_commit_stats_summary_handles_empty(mocked_github_service):
    assert GithubService.get_commit_stats_summary(None) == "No commit stats to display."


def test_get_contributions_last_6_months_uses_org_name_and_only_contributed(
    mocker, mocked_github_service
):
    # Patch now() to a fixed date to make timedelta deterministic if needed
    with patch("taskjournal.services.github.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 8, 16, 12, 0, 0)
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        fake_stats = [
            RepoCommitStat(repo="a", your_commits=2, total_commits=4, percentage=50.0)
        ]

        # Spy on summary + get_org_commit_stats
        mock_get_org = mocker.patch.object(
            GithubService, "get_org_commit_stats", return_value=fake_stats
        )
        mock_summary = mocker.spy(GithubService, "get_commit_stats_summary")

        out = mocked_github_service.get_contributions_last_6_months()

        assert mock_get_org.call_count == 1

        # Ensure we return the summary of the fake stats
        assert mock_summary.call_count == 1
        assert "Overall Contribution Summary" in out
