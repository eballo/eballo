from typer import Typer
from typer.testing import CliRunner


# ==========================================================
# 🌟 Positive Scenarios
# ==========================================================


def test_backup_run_happy_path(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["backup", "run"])

    # then
    assert result.exit_code == 0
    manager_instance.create_backup.assert_called_once()
