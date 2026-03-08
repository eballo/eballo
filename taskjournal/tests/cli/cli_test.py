from pytest_mock import MockerFixture

from typer import Typer
from typer.testing import CliRunner

from taskjournal.cli.main import app


class TestCli:

    def test_main_app__is_typer_and_exposes_commands(self) -> None:
        # when
        assert isinstance(app, Typer)

        result = CliRunner().invoke(app, ["--help"])

        # then
        assert result.exit_code == 0

        for name in ("daily", "week", "month", "half-year", "retro"):
            assert name in result.stdout

    def test_main_app_version_option_runs_version_callback(
        self, mocker: MockerFixture
    ) -> None:
        # given
        configure_logging = mocker.patch("taskjournal.cli.cli.configure_logging")
        logger = mocker.patch("taskjournal.cli.cli.logger")

        # when
        result = CliRunner().invoke(app, ["--version"])

        # then
        assert result.exit_code == 0
        configure_logging.assert_called_once()
        logger.info.assert_called_once()
