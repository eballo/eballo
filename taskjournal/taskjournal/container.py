from dependency_injector import containers, providers

import taskjournal.config as config
from taskjournal.commands.commands import CommandManager
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.backup import BackupService
from taskjournal.services.ai.base import NullAIService
from taskjournal.services.ai.claude_code import ClaudeCodeService
from taskjournal.services.file import FileService
from taskjournal.services.calendar.fireman import FiremanService
from taskjournal.services.integrations.github import GithubService
from taskjournal.services.calendar.holidays import HolidayService
from taskjournal.services.integrations.jira import JiraService
from taskjournal.services.migration import MigrationService
from taskjournal.services.ai.openai import OpenAIService
from taskjournal.services.parser import DailyParserService
from taskjournal.services.setup import SetupService
from taskjournal.services.task_manager import TaskManager
from taskjournal.services.time import TimeService
from taskjournal.services.wifi import WifiService
from taskjournal.services.calendar.working_days import WorkingDaysService


class AppContainer(containers.DeclarativeContainer):
    # Stateless utilities — singletons with no dependencies
    file_service = providers.Singleton(FileService)
    time_service = providers.Singleton(TimeService)

    # Core services — all config values injected here, not in the service files
    jira = providers.Singleton(
        JiraService,
        api_token=config.JIRA_API_TOKEN,
        email=config.JIRA_EMAIL,
        board_id=config.JIRA_BOARD_ID,
        organization=config.JIRA_ORGANIZATION,
    )
    github = providers.Singleton(
        GithubService,
        token=config.GIT_HUB_TOKEN,
        org_name=config.GIT_HUB_ORGANIZATION_NAME,
    )
    openai = providers.Singleton(
        OpenAIService,
        api_key=config.OPENAI_API_KEY,
    )
    claude_code = providers.Singleton(ClaudeCodeService)
    null_ai = providers.Singleton(NullAIService)

    # Selects the active AI service based on AI_PROVIDER config value
    # Accepted values: "openai", "claude_code", "none"
    ai_service = providers.Selector(
        lambda: config.AI_PROVIDER if config.AI_PROVIDER in ("openai", "claude_code") else "none",
        openai=openai,
        claude_code=claude_code,
        none=null_ai,
    )

    backup_service = providers.Singleton(
        BackupService,
        backup_dir=config.BACKUP_DIR,
        base_dir=config.BASE_DIR,
    )
    wifi_service = providers.Singleton(
        WifiService,
        home_wifi=config.HOME_WIFI,
        office_wifi=config.OFFICE_WIFI,
    )

    setup_service = providers.Singleton(SetupService)
    task_formatter = providers.Singleton(TaskFormatter)
    daily_parser = providers.Singleton(DailyParserService)

    # Services with runtime dependencies — factories (args passed at call time)
    holiday_service = providers.Factory(HolidayService)
    fireman_service = providers.Factory(FiremanService)

    # year passed at call time; parser is injected
    working_days_service = providers.Factory(
        WorkingDaysService,
        parser=daily_parser,
    )

    # Task manager — singleton with injected parser and wifi
    task_manager = providers.Singleton(
        TaskManager,
        parser=daily_parser,
        wifi_service=wifi_service,
    )

    # Composite services
    migration = providers.Singleton(
        MigrationService,
        task_formatter=task_formatter,
        parser=daily_parser,
        task_manager=task_manager,
    )

    command_manager = providers.Factory(
        CommandManager,
        jira=jira,
        github=github,
        task_formatter=task_formatter,
        ai_service=ai_service,
        parser=daily_parser,
        task_manager=task_manager,
        backup_service=backup_service,
        file_service=file_service,
        time_service=time_service,
    )
