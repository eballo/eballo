from datetime import datetime

from typer import Exit, Typer, Context, Option

from taskjournal.cli import version as app_version
from taskjournal.container import AppContainer
from taskjournal.cli.commands.backup import build_app as build_backup
from taskjournal.cli.commands.daily import build_app as build_daily
from taskjournal.cli.commands.half_year import build_app as build_half_year
from taskjournal.cli.commands.fireman import build_app as build_fireman
from taskjournal.cli.commands.holidays import build_app as build_holidays
from taskjournal.cli.commands.doctor import build_app as build_doctor
from taskjournal.cli.commands.info import build_app as build_info
from taskjournal.cli.commands.migrate import build_app as build_migrate
from taskjournal.cli.commands.setup import build_app as build_setup
from taskjournal.cli.commands.month import build_app as build_month
from taskjournal.cli.commands.one_on_one import build_app as build_one_on_one
from taskjournal.cli.commands.retro import build_app as build_retro
from taskjournal.cli.commands.search import build_app as build_search
from taskjournal.cli.commands.services import build_app as build_services
from taskjournal.cli.commands.statistics import build_app as build_statistics
from taskjournal.cli.commands.week import build_app as build_week
from taskjournal.cli.help_order import GroupedHelpOrder
from taskjournal.services.logger import logger, configure_logging

APP_NAME = "wk"


def _version_callback(value: bool) -> None:
    if value:
        configure_logging()
        logger.info(f"{APP_NAME} {app_version}")
        raise Exit()


def create_app(container: AppContainer | None = None) -> Typer:
    app = Typer(
        cls=GroupedHelpOrder,
        name=APP_NAME,
        rich_markup_mode="rich",
        pretty_exceptions_enable=False,
        help=(
            "Task Journal CLI.\n\n"
            "A CLI tool to organize your work by managing notes, summaries, reports. \n\n"
            "Helping you stay on track and communicate progress effectively.\n\n"
            "Use --help on any command to see detailed options and examples."
        ),
        no_args_is_help=True,
    )

    app.add_typer(build_daily(), name="daily", rich_help_panel="📋 Daily workflow")
    # Reports
    app.add_typer(build_week(), name="week", rich_help_panel="📊 Reports")
    app.add_typer(build_month(), name="month", rich_help_panel="📊 Reports")
    app.add_typer(build_half_year(), name="half-year", rich_help_panel="📊 Reports")
    app.add_typer(build_retro(), name="retro", rich_help_panel="📊 Reports")
    app.add_typer(build_one_on_one(), name="1on1", rich_help_panel="📊 Reports")
    # Tools
    app.add_typer(build_services(), name="services", rich_help_panel="🗂️ Tools")
    app.add_typer(build_backup(), name="backup", rich_help_panel="🗂️ Tools")
    app.add_typer(build_migrate(), name="migrate", rich_help_panel="🗂️ Tools")
    app.add_typer(build_fireman(), name="fireman", rich_help_panel="🗂️ Tools")
    app.add_typer(build_holidays(), name="holidays", rich_help_panel="🗂️ Tools")
    app.add_typer(build_statistics(), name="statistics", rich_help_panel="🗂️ Tools")
    app.add_typer(build_info(), name="info", rich_help_panel="🗂️ Tools")
    app.add_typer(build_setup(), name="setup", rich_help_panel="🗂️ Tools")
    app.add_typer(build_doctor(), name="doctor", rich_help_panel="🗂️ Tools")
    app.add_typer(build_search(), name="search", rich_help_panel="🗂️ Tools")

    if container is None:
        container = AppContainer()

    # Root callback (global flags)
    @app.callback()
    def _root(
        ctx: Context,
        _version: bool = Option(
            False,
            "--version",
            help="Show the application version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
        debug: bool = Option(
            False,
            "--debug",
            help="Enable debug logging (verbose output).",
            show_default=True,
        ),
    ) -> None:
        configure_logging(debug)

        obj = ctx.ensure_object(dict)
        obj.update(
            {
                "version": app_version,
                "debug": debug,
                "container": container,
                "manager": container.command_manager(debug=debug),
                "today": datetime.now(),
            }
        )

    return app
