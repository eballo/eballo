from datetime import datetime

from freezegun import freeze_time
from typer import Typer
from typer.testing import CliRunner


# ==========================================================
# 🌟 Positive Scenarios
# ==========================================================


@freeze_time("2025-01-19 10:00:00")
def test_half_year_report_happy_path(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    manager_instance.create_half_year_review = mocker.AsyncMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["half-year", "report"])

    # then
    assert result.exit_code == 0
    manager_instance.create_half_year_review.assert_awaited_once_with(
        datetime(2025, 1, 19, 10, 0, 0)
    )
