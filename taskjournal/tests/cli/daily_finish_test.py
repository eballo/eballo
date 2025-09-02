from datetime import datetime

from _pytest.logging import LogCaptureFixture
from freezegun import freeze_time
from typer import Typer
from typer.testing import CliRunner


# ==========================================================
# 🌟 Positive Scenarios
# ==========================================================


@freeze_time("2025-01-19 10:00:00")
def test_daily_finish_happy_path(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["daily", "finish"])

    # then
    assert result.exit_code == 0
    manager_instance.finalize_daily_notes.assert_called_once_with(
        datetime(2025, 1, 19, 10, 0, 0)
    )


@freeze_time("2025-01-19 10:00:00")
def test_daily_finish_debug(
    mocker, app: Typer, runner: CliRunner, caplog: LogCaptureFixture
):
    # given
    manager_instance = mocker.MagicMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["--debug", "daily", "finish"])

    # then
    assert result.exit_code == 0
    manager_instance.finalize_daily_notes.assert_called_once_with(
        datetime(2025, 1, 19, 10, 0, 0)
    )
    assert "date=None, debug=True" in caplog.text


@freeze_time("2025-01-19 10:00:00")
def test_daily_finish_date(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["daily", "finish", "--date", "2025-01-20 10:00"])

    # then
    assert result.exit_code == 0
    manager_instance.finalize_daily_notes.assert_called_once_with(
        datetime(2025, 1, 20, 10, 0, 0)
    )


# ==========================================================
# ⚡ Negative Scenarios
# ==========================================================


def test_daily_finish_date__no_valid_value(
    mocker, app: Typer, runner: CliRunner, caplog: LogCaptureFixture
):
    # given
    manager_instance = mocker.MagicMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["daily", "finish", "--date", "some-invalid-value"])

    # then
    assert result.exit_code == 1
    assert "❌ Invalid date format. Use 'YYYY-MM-DD HH:MM'." in caplog.text
    manager_instance.finalize_daily_notes.assert_not_called()
