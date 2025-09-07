from __future__ import annotations

from typer import Typer
from typer.testing import CliRunner

from taskjournal.cli.main import app


def test_main_app__is_typer_and_exposes_commands() -> None:
    # given
    assert isinstance(app, Typer)

    # when
    result = CliRunner().invoke(app, ["--help"])

    # then
    assert result.exit_code == 0

    for name in ("daily", "week", "month", "half-year", "retro"):
        assert name in result.stdout
