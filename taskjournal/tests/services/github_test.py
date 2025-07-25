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
