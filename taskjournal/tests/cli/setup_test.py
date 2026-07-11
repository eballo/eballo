from collections.abc import Callable
from pathlib import Path

from dependency_injector import providers
from pytest_mock import MockerFixture
from typer.testing import Result

from taskjournal.container import AppContainer
from taskjournal.services.setup import _DEFAULTS


class TestSetupCLI:

    def _mock_wizard(
        self,
        mocker: MockerFixture,
        cli_container: AppContainer,
        env_exists: bool = False,
        confirm_values: list[bool] | None = None,
        prompt_side_effect: list[str] | None = None,
    ) -> tuple:
        env_path = mocker.MagicMock(spec=Path)
        env_path.exists.return_value = env_exists
        mocker.patch("taskjournal.cli.commands.setup.ENV_PATH", env_path)

        service_mock = mocker.MagicMock()
        service_mock.load_existing.return_value = dict(_DEFAULTS)
        service_mock.is_configured.return_value = False
        cli_container.setup_service.override(providers.Object(service_mock))

        if confirm_values is not None:
            mocker.patch("taskjournal.cli.commands.setup.confirm", side_effect=confirm_values)
        if prompt_side_effect is not None:
            mocker.patch("taskjournal.cli.commands.setup.prompt", side_effect=prompt_side_effect)
        else:
            mocker.patch("taskjournal.cli.commands.setup.prompt", return_value="value")

        return service_mock, env_path

    def test_setup_cancelled_when_user_declines_update(
        self,
        mocker: MockerFixture,
        cli_container: AppContainer,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        service_mock, _ = self._mock_wizard(mocker, cli_container, env_exists=True, confirm_values=[False])

        result = invoke_cli(["setup"])

        assert result.exit_code == 0
        service_mock.write_env.assert_not_called()

    def test_setup_full_wizard_no_existing_config(
        self,
        mocker: MockerFixture,
        cli_container: AppContainer,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # confirms: paths, jira, github, wifi, screen_time, alarms, data_files (AI is a prompt)
        confirms = [True, True, True, True, False, True, True]
        prompts = ["md", "/notes", "/backup",               # paths
                   "org", "email@x.com", "token", "123",   # jira
                   "gh-token", "org-name",                  # github
                   "claude_code",                          # AI provider (no key needed)
                   "HomeWifi", "OfficeWifi",                # wifi
                   "Obsidian",                             # editor
                   "Alice"]                                # manager name
        service_mock, _ = self._mock_wizard(mocker, cli_container, env_exists=False, confirm_values=confirms, prompt_side_effect=prompts)

        result = invoke_cli(["setup"])

        assert result.exit_code == 0
        service_mock.write_env.assert_called_once()

    def test_setup_skips_integrations_when_declined(
        self,
        mocker: MockerFixture,
        cli_container: AppContainer,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # existing config → yes to update, no to paths/jira/github/wifi/screen_time/alarms, yes to data files
        # AI section is always a prompt (no confirm for it)
        confirms = [True, False, False, False, False, False, False, True]
        service_mock, _ = self._mock_wizard(mocker, cli_container, env_exists=True, confirm_values=confirms,
                                            prompt_side_effect=["claude_code", "Obsidian", ""])

        result = invoke_cli(["setup"])

        assert result.exit_code == 0
        service_mock.write_env.assert_called_once()
        service_mock.create_data_files.assert_called_once()

    def test_setup_invalid_format_retries(
        self,
        mocker: MockerFixture,
        cli_container: AppContainer,
        invoke_cli: Callable[[list[str]], Result],
    ) -> None:
        # confirms: paths, no-jira, no-github, no-wifi, no-screen_time, no-alarms, no-data_files
        confirms = [True, False, False, False, False, False, False]
        # First prompt (format) returns invalid then valid, then the rest
        prompts = ["xml", "md", "/notes", "/backup", "claude_code", "Obsidian", ""]
        service_mock, _ = self._mock_wizard(mocker, cli_container, env_exists=False, confirm_values=confirms,
                                            prompt_side_effect=prompts)

        result = invoke_cli(["setup"])

        assert result.exit_code == 0
        service_mock.write_env.assert_called_once()
