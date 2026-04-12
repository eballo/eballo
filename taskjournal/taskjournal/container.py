from dependency_injector import containers, providers

from taskjournal.commands.commands import CommandManager
from taskjournal.repositories.task_formatter import TaskFormatter
from taskjournal.services.github import GithubService
from taskjournal.services.holidays import HolidayService
from taskjournal.services.jira import JiraService
from taskjournal.services.migration import MigrationService
from taskjournal.services.openai import OpenAIService
from taskjournal.services.parser import DailyParserService
from taskjournal.services.working_days import WorkingDaysService


class AppContainer(containers.DeclarativeContainer):
    # Core services — shared singletons (created once per container instance)
    jira = providers.Singleton(JiraService)
    github = providers.Singleton(GithubService)
    openai = providers.Singleton(OpenAIService)
    task_formatter = providers.Singleton(TaskFormatter)
    daily_parser = providers.Singleton(DailyParserService)

    # Services with runtime dependencies — factories (created per invocation)
    # filepath is passed at call time: container.holiday_service(filepath=...)
    holiday_service = providers.Factory(HolidayService)

    # year (and optionally debug) are passed at call time; parser is injected
    working_days_service = providers.Factory(
        WorkingDaysService,
        parser=daily_parser,
    )

    # Composite services
    migration = providers.Singleton(
        MigrationService,
        task_formatter=task_formatter,
        parser=daily_parser,
    )

    command_manager = providers.Factory(
        CommandManager,
        jira=jira,
        github=github,
        task_formatter=task_formatter,
        openai=openai,
        parser=daily_parser,
    )
