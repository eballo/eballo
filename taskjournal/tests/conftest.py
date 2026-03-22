from collections.abc import Callable, Sequence
from datetime import date, datetime
from os.path import join
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, AsyncMock

from pytest import MonkeyPatch, fixture
from pytest_mock import MockerFixture
from typer import Typer
from typer.testing import CliRunner, Result

from taskjournal.cli.cli import create_app
from taskjournal.commands.commands import CommandManager
from taskjournal.services.daily import DailyService
from taskjournal.services.file import get_week_folder
from taskjournal.services.fireman import FiremanService
from taskjournal.services.github import GithubService
from taskjournal.services.holidays import HolidayService
from taskjournal.services.jira import JiraService
from taskjournal.services.migration import MigrationService
from taskjournal.services.openai import OpenAIService
from taskjournal.services.parser import DailyParserService
from taskjournal.services.report import ReportService
from taskjournal.services.wifi import WifiService
from taskjournal.services.working_days import WorkingDaysService


@fixture()
def app() -> Typer:
    return create_app()


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
    return get_week_folder(base_dir, today)


@fixture
def cli_manager(mocker: MockerFixture) -> MagicMock:
    manager = mocker.MagicMock()
    mocker.patch("taskjournal.cli.cli.CommandManager", return_value=manager)
    return manager


@fixture
def cli_jira(cli_manager: MagicMock, mocker: MockerFixture) -> MagicMock:
    cli_manager.jira = mocker.MagicMock()
    return cli_manager.jira


@fixture
def cli_github(cli_manager: MagicMock, mocker: MockerFixture) -> MagicMock:
    cli_manager.github = mocker.MagicMock()
    return cli_manager.github


@fixture
def fixed_datetime() -> datetime:
    return datetime(2025, 1, 15, 9, 30, 0)


@fixture
def cmd(mocker: MockerFixture) -> CommandManager:
    mocker.patch(
        "taskjournal.commands.commands.JiraService",
        return_value=mocker.MagicMock(name="JiraServiceMock"),
    )
    mocker.patch(
        "taskjournal.commands.commands.GithubService",
        return_value=mocker.MagicMock(name="GithubServiceMock"),
    )
    mocker.patch(
        "taskjournal.commands.commands.TaskFormatter",
        return_value=mocker.MagicMock(name="TaskFormatterMock"),
    )
    mocker.patch(
        "taskjournal.commands.commands.OpenAIService",
        return_value=mocker.MagicMock(name="OpenAIServiceMock"),
    )
    mocker.patch(
        "taskjournal.commands.commands.DailyService",
        return_value=mocker.Mock(
            spec=DailyService,
            create_daily_notes=AsyncMock(),
            finalize_daily_notes=mocker.Mock(),
            daily_time=mocker.Mock(),
        ),
    )
    mocker.patch(
        "taskjournal.commands.commands.ReportService",
        return_value=mocker.Mock(
            spec=ReportService,
            create_week_report=AsyncMock(),
            create_month_review=AsyncMock(),
            create_half_year_review=AsyncMock(),
            create_retro=mocker.Mock(),
            create_1on1=mocker.Mock(),
        ),
    )
    return CommandManager()


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
def backup_source_dir(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    (tmp_path / "note1.txt").write_text("Note 1")
    (tmp_path / "subfolder").mkdir()
    (tmp_path / "subfolder" / "note2.txt").write_text("Note 2")
    monkeypatch.setattr("taskjournal.services.backup.BASE_DIR", tmp_path)
    return tmp_path


@fixture
def backup_output_dir(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    backup_path = tmp_path / "backups"
    monkeypatch.setenv("BACKUP_DIR", str(backup_path))
    monkeypatch.setattr("taskjournal.services.backup.BACKUP_DIR", backup_path)
    return backup_path


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
    return JiraService()


@fixture
def github_service() -> GithubService:
    return GithubService()


@fixture
def openai_chat_completions_url() -> str:
    return "https://api.openai.com/v1/chat/completions"


@fixture
def openai_service() -> OpenAIService:
    return OpenAIService()


@fixture
def wifi_service() -> WifiService:
    return WifiService()


@fixture
def wifi_subprocess_run(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("taskjournal.services.wifi.subprocess.run")


@fixture
def wifi_result_factory() -> Callable[[str], MagicMock]:
    def _make(stdout: str) -> MagicMock:
        result = MagicMock()
        result.stdout = stdout
        return result

    return _make


@fixture
def migration_service() -> MigrationService:
    return MigrationService()


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
