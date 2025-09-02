from typer import Typer
from typer.testing import CliRunner


# ==========================================================
# 🌟 Positive Scenarios
# ==========================================================


def test_services_jira_happy_path(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    manager_instance.jira = mocker.MagicMock()

    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["services", "jira"])

    # then
    assert result.exit_code == 0
    manager_instance.jira.get_current_sprint_tasks_not_done_assigned_to_me.assert_called_once()


def test_services_git_happy_path(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    manager_instance.github = mocker.MagicMock()

    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(
        app,
        [
            "services",
            "git",
            "--contributed",
            "--stats",
        ],
    )

    # then
    assert result.exit_code == 0
    manager_instance.github.get_org_commit_stats.assert_called_once()
