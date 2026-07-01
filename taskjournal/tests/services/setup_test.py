from pathlib import Path

from pytest import fixture
from pytest_mock import MockerFixture

from taskjournal.config import TEMPLATE_FORMAT
from taskjournal.services.setup import SetupService, _DEFAULTS, ENV_PATH


@fixture
def service() -> SetupService:
    return SetupService()


class TestSetupService:

    def test_load_existing_returns_defaults_when_no_env_file(
        self,
        mocker: MockerFixture,
        service: SetupService,
    ) -> None:
        mocker.patch.object(Path, "exists", return_value=False)

        result = service.load_existing()

        assert result["TEMPLATE_FORMAT"] == "md"
        assert result["JIRA_API_TOKEN"] == "your-jira-key"
        assert result == _DEFAULTS

    def test_load_existing_parses_env_file(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        service: SetupService,
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            'BASE_DIR=/custom/path\nJIRA_API_TOKEN="real-token"\n# comment\n\n',
            encoding="utf-8",
        )
        mocker.patch("taskjournal.services.setup.ENV_PATH", env_file)

        result = service.load_existing()

        assert result["BASE_DIR"] == "/custom/path"
        assert result["JIRA_API_TOKEN"] == "real-token"
        assert result["TEMPLATE_FORMAT"] == "md"

    def test_load_existing_logs_warning_on_read_failure(
        self,
        mocker: MockerFixture,
        service: SetupService,
    ) -> None:
        mock_path = mocker.MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.read_text.side_effect = OSError("disk error")
        mocker.patch("taskjournal.services.setup.ENV_PATH", mock_path)
        mock_logger = mocker.patch("taskjournal.services.setup.logger")

        result = service.load_existing()

        mock_logger.warning.assert_called_once()
        assert result["TEMPLATE_FORMAT"] == "md"

    def test_write_env_creates_file_with_all_keys(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        service: SetupService,
    ) -> None:
        env_file = tmp_path / "config" / ".env"
        mocker.patch("taskjournal.services.setup.ENV_PATH", env_file)

        values = dict(_DEFAULTS)
        values["BASE_DIR"] = "/my/notes"
        values["JIRA_API_TOKEN"] = "tok123"

        service.write_env(values)

        content = env_file.read_text()
        assert "BASE_DIR=/my/notes" in content
        assert "JIRA_API_TOKEN=tok123" in content
        assert "TEMPLATE_FORMAT=md" in content
        assert "HOME_WIFI=" in content

    def test_write_env_preserves_extra_user_keys(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        service: SetupService,
    ) -> None:
        env_file = tmp_path / "config" / ".env"
        mocker.patch("taskjournal.services.setup.ENV_PATH", env_file)

        values = dict(_DEFAULTS)
        values["MY_CUSTOM_VAR"] = "custom_value"
        values["ANOTHER_KEY"] = "another_value"

        service.write_env(values)

        content = env_file.read_text()
        assert "MY_CUSTOM_VAR=custom_value" in content
        assert "ANOTHER_KEY=another_value" in content
        assert "TEMPLATE_FORMAT=md" in content

    def test_is_configured_returns_false_for_default_value(
        self,
        service: SetupService,
    ) -> None:
        values = dict(_DEFAULTS)
        assert service.is_configured("JIRA_API_TOKEN", values) is False

    def test_is_configured_returns_true_for_custom_value(
        self,
        service: SetupService,
    ) -> None:
        values = dict(_DEFAULTS)
        values["JIRA_API_TOKEN"] = "actual-token"
        assert service.is_configured("JIRA_API_TOKEN", values) is True

    def test_is_configured_returns_false_for_empty_value(
        self,
        service: SetupService,
    ) -> None:
        values: dict[str, str] = {"SOME_KEY": ""}
        assert service.is_configured("SOME_KEY", values) is False

    def test_create_data_files_creates_both_files(
        self,
        tmp_path: Path,
        service: SetupService,
    ) -> None:
        service.create_data_files(str(tmp_path), 2026)

        holidays_path = tmp_path / "2026" / "holidays" / f"holidays.{TEMPLATE_FORMAT}"
        fireman_path = tmp_path / "2026" / "fireman" / f"fireman_weeks.{TEMPLATE_FORMAT}"

        assert holidays_path.exists()
        assert fireman_path.exists()
        assert "2026" in holidays_path.read_text()
        assert "2026" in fireman_path.read_text()

    def test_create_data_files_skips_existing_files(
        self,
        tmp_path: Path,
        mocker: MockerFixture,
        service: SetupService,
    ) -> None:
        holidays_path = tmp_path / "2026" / "holidays" / f"holidays.{TEMPLATE_FORMAT}"
        holidays_path.parent.mkdir(parents=True)
        holidays_path.write_text("existing content", encoding="utf-8")
        mock_logger = mocker.patch("taskjournal.services.setup.logger")

        service.create_data_files(str(tmp_path), 2026)

        assert holidays_path.read_text() == "existing content"
        mock_logger.debug.assert_called()

    def test_create_data_files_uses_txt_extension_when_template_format_is_txt(
        self,
        tmp_path: Path,
        service: SetupService,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch("taskjournal.services.setup.TEMPLATE_FORMAT", "txt")

        service.create_data_files(str(tmp_path), 2026)

        assert (tmp_path / "2026" / "holidays" / "holidays.txt").exists()
        assert (tmp_path / "2026" / "fireman" / "fireman_weeks.txt").exists()
        assert not (tmp_path / "2026" / "holidays" / "holidays.md").exists()
