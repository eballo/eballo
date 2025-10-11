from datetime import datetime

from freezegun import freeze_time
from pytest import LogCaptureFixture
from typer import Typer
from typer.testing import CliRunner


# ==========================================================
# 🌟 Positive Scenarios
# ==========================================================


@freeze_time("2025-01-19 10:00:00")
def test_daily_start(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    manager_instance.create_daily_notes = mocker.AsyncMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["daily", "start"])

    # then
    assert result.exit_code == 0
    manager_instance.create_daily_notes.assert_called_once_with(
        datetime(2025, 1, 19, 10, 0, 0), False, False, None
    )


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_debug(
    mocker, app: Typer, runner: CliRunner, caplog: LogCaptureFixture
):
    # given
    manager_instance = mocker.MagicMock()
    manager_instance.create_daily_notes = mocker.AsyncMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["--debug", "daily", "start"])

    # then
    assert result.exit_code == 0
    manager_instance.create_daily_notes.assert_called_once_with(
        datetime(2025, 1, 19, 10, 0, 0), False, False, None
    )
    assert "date=None, force=False, debug=True" in caplog.text


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_force(
    mocker, app: Typer, runner: CliRunner, caplog: LogCaptureFixture
):
    # given
    manager_instance = mocker.MagicMock()
    manager_instance.create_daily_notes = mocker.AsyncMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["daily", "start", "--force"])

    # then
    assert result.exit_code == 0
    manager_instance.create_daily_notes.assert_called_once_with(
        datetime(2025, 1, 19, 10, 0, 0), True, False, None
    )
    assert (
        "Force option is enabled. Existing daily notes file will be overwritten."
        in caplog.text
    )


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_date(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    manager_instance.create_daily_notes = mocker.AsyncMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["daily", "start", "--date", "2025-01-20 10:00"])

    # then
    assert result.exit_code == 0
    manager_instance.create_daily_notes.assert_called_once_with(
        datetime(2025, 1, 20, 10, 0, 0), False, False, None
    )


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_date_and_force(
    mocker, app: Typer, runner: CliRunner, caplog: LogCaptureFixture
):
    # given
    manager_instance = mocker.MagicMock()
    manager_instance.create_daily_notes = mocker.AsyncMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(
        app, ["daily", "start", "--date", "2025-01-20 10:00", "--force"]
    )

    # then
    assert result.exit_code == 0
    manager_instance.create_daily_notes.assert_called_once_with(
        datetime(2025, 1, 20, 10, 0, 0), True, False, None
    )
    assert (
        "Force option is enabled. Existing daily notes file will be overwritten."
        in caplog.text
    )


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_firefighter(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    manager_instance.create_daily_notes = mocker.AsyncMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["daily", "start", "--ff"])

    # then
    assert result.exit_code == 0
    manager_instance.create_daily_notes.assert_called_once_with(
        datetime(2025, 1, 19, 10, 0, 0), False, True, None
    )


@freeze_time("2025-01-19 10:00:00")
def test_daily_start_work_from(mocker, app: Typer, runner: CliRunner):
    # given
    manager_instance = mocker.MagicMock()
    manager_instance.create_daily_notes = mocker.AsyncMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["daily", "start", "--w", "home"])

    # then
    assert result.exit_code == 0
    manager_instance.create_daily_notes.assert_called_once_with(
        datetime(2025, 1, 19, 10, 0, 0), False, False, "home"
    )


# ==========================================================
# ⚡ Negative Scenarios
# ==========================================================


def test_daily_start_date__no_valid_value(
    mocker, app: Typer, runner: CliRunner, caplog: LogCaptureFixture
):
    # given
    manager_instance = mocker.MagicMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager_instance)

    # when
    result = runner.invoke(app, ["daily", "start", "--date", "some-invalid-value"])

    # then
    assert result.exit_code == 1
    assert "❌ Invalid date format. Use 'YYYY-MM-DD HH:MM'." in caplog.text
    manager_instance.create_daily_notes.assert_not_called()
