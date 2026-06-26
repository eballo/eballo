from collections.abc import Callable, Sequence
from os.path import join
from pathlib import Path
from datetime import date, datetime
from textwrap import dedent
from unittest.mock import MagicMock

from dependency_injector import providers
from pytest import fixture
from pytest_mock import MockerFixture
from typer import Typer
from typer.testing import CliRunner, Result

from taskjournal.cli.cli import create_app
from taskjournal.commands.commands import CommandManager
from taskjournal.container import AppContainer
from taskjournal.services.base import HealthCheckResult, ServiceStatus
from taskjournal.services.file import FileService
from taskjournal.services.fireman import FiremanService
from taskjournal.services.github import GithubService
from taskjournal.services.holidays import HolidayService
from taskjournal.services.jira import JiraService
from taskjournal.services.migration import MigrationService
from taskjournal.services.openai import OpenAIService
from taskjournal.services.parser import DailyParserService
from taskjournal.services.wifi import WifiService
from taskjournal.services.working_days import WorkingDaysService


@fixture
def cli_container(mocker: MockerFixture) -> AppContainer:
    """Real AppContainer with all external services overridden by mocks."""
    _ok = HealthCheckResult(status=ServiceStatus.OK, message="Mocked")

    def _mock_svc(name: str) -> MagicMock:
        m = mocker.MagicMock(name=name)
        m.health_check.return_value = _ok
        return m

    container = AppContainer()
    container.jira.override(providers.Object(_mock_svc("JiraServiceMock")))
    container.github.override(providers.Object(_mock_svc("GithubServiceMock")))
    container.openai.override(providers.Object(_mock_svc("OpenAIServiceMock")))
    container.wifi_service.override(providers.Object(_mock_svc("WifiServiceMock")))
    container.task_formatter.override(providers.Object(mocker.MagicMock(name="TaskFormatterMock")))
    container.daily_parser.override(providers.Object(mocker.MagicMock(name="DailyParserMock")))
    yield container
    container.reset_override()


@fixture()
def app(cli_container: AppContainer) -> Typer:
    return create_app(container=cli_container)


@fixture()
def runner() -> CliRunner:
    return CliRunner()


@fixture()
def invoke_cli(app: Typer, runner: CliRunner) -> Callable[[Sequence[str]], Result]:
    def _invoke(args: Sequence[str]) -> Result:
        return runner.invoke(app, list(args))

    return _invoke


@fixture
def fixture_path() -> Path:
    return Path(__file__).parent / "commands/fixtures"


@fixture
def base_dir() -> str:
    return "/mocked/path/Documents/DailyNotes/"


@fixture
def base_project() -> str:
    return "/mocked/path/Documents/work/personal/eballo/taskjournal/taskjournal/"


@fixture
def daily_notes_path(today: datetime, week_folder: str) -> str:
    return join(week_folder, f"{today.strftime('%Y-%m-%d')}-DailyNotes.txt")


@fixture
def daily_notes_template(base_project: str) -> str:
    return join(base_project, "templates/dailyNotes.txt")


@fixture
def retro_template(base_project: str) -> str:
    return join(base_project, "templates/retro.txt")


@fixture
def week_summary_template(base_project: str) -> str:
    return join(base_project, "templates/weekSummary.txt")


@fixture
def half_year_template(base_project: str) -> str:
    return join(base_project, "templates/half-year.txt")


@fixture
def today() -> datetime:
    return datetime(2025, 1, 19)  # Use a fixed date for testing


@fixture
def week_folder(base_dir: str, today: datetime) -> str:
    return FileService.get_week_folder(base_dir, today)


@fixture
def cli_manager(cli_container: AppContainer, mocker: MockerFixture) -> MagicMock:
    manager = mocker.MagicMock(name="CommandManagerMock")
    manager.get_previous_day_issues.return_value = None
    cli_container.command_manager.override(providers.Object(manager))
    return manager


@fixture
def cli_jira(cli_manager: MagicMock) -> MagicMock:
    return cli_manager.jira


@fixture
def cli_github(cli_manager: MagicMock) -> MagicMock:
    return cli_manager.github


@fixture
def cli_migration(cli_container: AppContainer, mocker: MockerFixture) -> MagicMock:
    """Provides a mock MigrationService from the CLI container."""
    service = mocker.MagicMock(name="MigrationServiceMock")
    cli_container.migration.override(providers.Object(service))
    return service


@fixture
def cli_working_days(
    cli_container: AppContainer, mocker: MockerFixture
) -> tuple[MagicMock, MagicMock]:
    """Provides a mock WorkingDaysService factory and instance.

    Returns (factory_mock, service_mock) so tests can assert on call arguments
    (e.g. factory.assert_called_once_with(year=2026, debug=False)) and on
    service method calls (e.g. service.summary.assert_called_once()).
    """
    service = mocker.MagicMock(name="WorkingDaysServiceMock")
    factory = mocker.MagicMock(name="WorkingDaysFactoryMock", return_value=service)
    cli_container.working_days_service.override(providers.Factory(factory))
    return factory, service


@fixture
def fixed_datetime() -> datetime:
    return datetime(2025, 1, 15, 9, 30, 0)


@fixture
def cmd(mocker: MockerFixture) -> CommandManager:
    time_service = mocker.MagicMock(name="TimeServiceMock")
    time_service.get_accumulated_week_seconds.return_value = 0
    time_service.estimated_finish_time.return_value = datetime(2025, 1, 15, 18, 0, 0)
    return CommandManager(
        jira=mocker.MagicMock(name="JiraServiceMock"),
        github=mocker.MagicMock(name="GithubServiceMock"),
        task_formatter=mocker.MagicMock(name="TaskFormatterMock"),
        openai=mocker.MagicMock(name="OpenAIServiceMock"),
        parser=mocker.MagicMock(name="DailyParserServiceMock"),
        task_manager=mocker.MagicMock(name="TaskManagerMock"),
        backup_service=mocker.MagicMock(name="BackupServiceMock"),
        file_service=mocker.MagicMock(name="FileServiceMock"),
        time_service=time_service,
    )


@fixture
def temp_week_folder(tmp_path: Path) -> str:
    return str(tmp_path / "week3")


@fixture
def temp_holiday_file(tmp_path: Path) -> str:
    content = dedent(
        """
    # From last year
    2026-01-02 - Old Holiday

    # National holidays
    2026-01-01 - New Year's Day
    2026-12-25 - Christmas

    # Malformed Section
    This is not a date
    """
    )
    file_path = tmp_path / "holidays.txt"
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)


@fixture
def backup_source_dir(tmp_path: Path) -> Path:
    (tmp_path / "note1.txt").write_text("Note 1")
    (tmp_path / "subfolder").mkdir()
    (tmp_path / "subfolder" / "note2.txt").write_text("Note 2")
    return tmp_path


@fixture
def backup_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "backups"


@fixture
def backup_service_instance(backup_source_dir: Path, backup_output_dir: Path) -> "BackupService":
    from taskjournal.services.backup import BackupService as _BS
    return _BS(backup_dir=str(backup_output_dir), base_dir=str(backup_source_dir))


@fixture
def mock_year_structure(tmp_path: Path, mocker: MockerFixture) -> str:
    year = "2026"
    year_dir = tmp_path / year
    year_dir.mkdir()
    content = dedent(
        """
        # Weekday Holiday
        2026-01-01 - New Year

        # Weekend Holiday (Saturday)
        2026-01-03 - Weekend Holiday

        # Another Weekday Holiday
        2026-01-06 - Epiphany
        """
    )
    holiday_file = year_dir / "holidays.txt"
    holiday_file.write_text(content, encoding="utf-8")
    mocker.patch("taskjournal.services.working_days.BASE_DIR", str(tmp_path))
    mocker.patch("taskjournal.services.working_days.HOLIDAYS_FILE", "holidays.txt")
    return year


@fixture
def mock_today(mocker: MockerFixture) -> date:
    class MockDate(date):
        @classmethod
        def today(cls) -> "MockDate":
            return cls(2026, 1, 10)

    mocker.patch("taskjournal.services.working_days.datetime", MockDate)
    return date(2026, 1, 10)


@fixture
def jira_service(mocker: MockerFixture) -> JiraService:
    mocker.patch("taskjournal.services.jira.JIRA", return_value=mocker.MagicMock())
    return JiraService(api_token="test-token", email="test@test.com", board_id="TEST", organization="testorg")


@fixture
def github_service() -> GithubService:
    return GithubService(token="fake-token", org_name="test-org")


@fixture
def openai_chat_completions_url() -> str:
    return "https://api.openai.com/v1/chat/completions"


@fixture
def openai_service() -> OpenAIService:
    return OpenAIService(api_key="test-key")


@fixture
def wifi_service() -> WifiService:
    return WifiService(home_wifi="CodePI", office_wifi="TSH")


@fixture
def wifi_subprocess_run(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("taskjournal.services.wifi.run")


@fixture
def wifi_result_factory() -> Callable[[str], MagicMock]:
    def _make(stdout: str) -> MagicMock:
        result = MagicMock()
        result.stdout = stdout
        return result

    return _make


@fixture
def migration_service(mocker: MockerFixture) -> MigrationService:
    return MigrationService(
        task_formatter=mocker.MagicMock(),
        parser=mocker.MagicMock(),
        task_manager=mocker.MagicMock(),
    )


@fixture
def daily_parser_service() -> DailyParserService:
    return DailyParserService()


@fixture
def holiday_service_factory() -> Callable[[str], HolidayService]:
    def _make(filepath: str) -> HolidayService:
        return HolidayService(filepath)

    return _make


@fixture
def fireman_service_factory() -> Callable[[datetime], FiremanService]:
    def _make(today: datetime) -> FiremanService:
        return FiremanService(today)

    return _make


@fixture
def working_days_service_factory() -> Callable[[str], WorkingDaysService]:
    def _make(year: str) -> WorkingDaysService:
        return WorkingDaysService(year)

    return _make
