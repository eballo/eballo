from collections.abc import Callable
from unittest.mock import MagicMock

from typer.testing import Result


class TestBackup:

    def test_backup_run_happy_path(
        self,
        cli_manager: MagicMock,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # given
        manager_instance = cli_manager

        # when
        result = invoke_cli(["backup", "run"])

        # then
        assert result.exit_code == 0
        manager_instance.create_backup.assert_called_once()
