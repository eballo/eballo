from datetime import datetime

from freezegun import freeze_time
from typer import Typer
from typer.testing import CliRunner


# ==========================================================
# 🌟 Positive Scenarios
# ==========================================================


@freeze_time("2025-01-19 10:00:00")
def test_daily_time_happy_path(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["daily", "time"])

    # then
    assert result.exit_code == 0
    manager_instance.daily_time.assert_called_once_with(datetime(2025, 1, 19, 10, 0, 0))
