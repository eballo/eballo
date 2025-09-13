from datetime import datetime
from unittest.mock import AsyncMock

from freezegun import freeze_time
from typer import Typer
from typer.testing import CliRunner


@freeze_time("2025-01-19 10:00:00")
def test_week_report_happy_path(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    manager_instance.create_week_summary = AsyncMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["week", "report"])

    # then
    assert result.exit_code == 0
    manager_instance.create_week_summary.assert_awaited_once_with(
        datetime(2025, 1, 19, 10, 0, 0)
    )


@freeze_time("2025-01-19 10:00:00")
def test_week_report_date(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    manager_instance.create_week_summary = AsyncMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["week", "report", "--date", "2025-01-20"])

    # then
    assert result.exit_code == 0
    manager_instance.create_week_summary.assert_awaited_once_with(
        datetime(2025, 1, 20, 0, 0, 0)
    )
