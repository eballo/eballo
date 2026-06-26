from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

from pytest_mock import MockerFixture
from typer.testing import Result

from taskjournal.services.base import HealthCheckResult, ServiceStatus


class TestDoctor:

    def test_doctor_all_ok_shows_summary(
        self,
        cli_container: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value")
        mocker.patch("taskjournal.cli.commands.doctor.ENV_PATH", env_file)

        result = invoke_cli(["doctor"])

        assert result.exit_code == 0
        assert "OK" in result.output

    def test_doctor_missing_env_file_shows_error(
        self,
        cli_container: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        missing = tmp_path / "nonexistent.env"
        mocker.patch("taskjournal.cli.commands.doctor.ENV_PATH", missing)

        result = invoke_cli(["doctor"])

        assert result.exit_code == 0
        assert "wk setup" in result.output

    def test_check_config_file_ok(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        from taskjournal.cli.commands.doctor import _check_config_file

        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value")
        mocker.patch("taskjournal.cli.commands.doctor.ENV_PATH", env_file)

        name, result = _check_config_file()

        assert name == "Config file"
        assert result.status == ServiceStatus.OK

    def test_check_config_file_missing(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
    ) -> None:
        from taskjournal.cli.commands.doctor import _check_config_file

        missing = tmp_path / "missing.env"
        mocker.patch("taskjournal.cli.commands.doctor.ENV_PATH", missing)

        name, result = _check_config_file()

        assert name == "Config file"
        assert result.status == ServiceStatus.ERROR
        assert len(result.details) > 0

    def test_print_report_counts_correctly(self) -> None:
        from io import StringIO

        from rich.console import Console

        from taskjournal.cli.commands.doctor import _print_report

        checks = [
            ("Svc A", HealthCheckResult(ServiceStatus.OK, "ok")),
            ("Svc B", HealthCheckResult(ServiceStatus.WARNING, "warn")),
            ("Svc C", HealthCheckResult(ServiceStatus.ERROR, "err")),
        ]
        buf = StringIO()
        import taskjournal.cli.commands.doctor as _mod
        original = _mod.console
        _mod.console = Console(file=buf, highlight=False)
        try:
            _print_report(checks)
        finally:
            _mod.console = original

        output = buf.getvalue()
        assert "1 OK" in output
        assert "1 warning" in output
        assert "1 error" in output
        assert "wk setup" in output

    def test_print_report_no_error_footer_when_all_ok(self) -> None:
        from io import StringIO

        from rich.console import Console

        from taskjournal.cli.commands.doctor import _print_report

        checks = [
            ("Svc A", HealthCheckResult(ServiceStatus.OK, "ok")),
        ]
        buf = StringIO()
        import taskjournal.cli.commands.doctor as _mod
        original = _mod.console
        _mod.console = Console(file=buf, highlight=False)
        try:
            _print_report(checks)
        finally:
            _mod.console = original

        output = buf.getvalue()
        assert "wk setup" not in output
