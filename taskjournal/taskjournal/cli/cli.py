from datetime import datetime

from typer import Exit, Typer, Context, Option

from taskjournal.cli import version as app_version
from taskjournal.cli.commands.backup import build_app as build_backup
from taskjournal.cli.commands.daily import build_app as build_daily
from taskjournal.cli.commands.half_year import build_app as build_half_year
from taskjournal.cli.commands.holidays import build_app as build_holidays
from taskjournal.cli.commands.migrate import build_app as build_migrate
from taskjournal.cli.commands.month import build_app as build_month
from taskjournal.cli.commands.one_on_one import build_app as build_one_on_one
from taskjournal.cli.commands.retro import build_app as build_retro
from taskjournal.cli.commands.services import build_app as build_services
from taskjournal.cli.commands.statistics import build_app as build_statistics
from taskjournal.cli.commands.week import build_app as build_week
from taskjournal.cli.help_order import GroupedHelpOrder
from taskjournal.commands.commands import CommandManager
from taskjournal.services.logger import logger, configure_logging

APP_NAME = "wk"


def _version_callback(value: bool):
    if value:
        configure_logging()
        logger.info(f"{APP_NAME} {app_version}")
        raise Exit()


def create_app() -> Typer:
    app = Typer(
        cls=GroupedHelpOrder,
        name=APP_NAME,
        help=(
            "Task Journal CLI.\n\n"
            "A CLI tool to organize your work by managing notes, summaries, reports. \n\n"
            "Helping you stay on track and communicate progress effectively.\n\n"
            "Use --help on any command to see detailed options and examples."
        ),
        no_args_is_help=True,
    )

    app.add_typer(build_daily(), name="daily")
    app.add_typer(build_week(), name="week")
    app.add_typer(build_one_on_one(), name="1on1")
    app.add_typer(build_retro(), name="retro")
    app.add_typer(build_month(), name="month")
    app.add_typer(build_half_year(), name="half-year")
    app.add_typer(build_services(), name="services", hidden=True)
    app.add_typer(build_backup(), name="backup", hidden=True)
    app.add_typer(build_migrate(), name="migrate", hidden=True)
    app.add_typer(build_holidays(), name="holidays")
    app.add_typer(build_statistics(), name="statistics")

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
    ):
        configure_logging(debug)

        obj = ctx.ensure_object(dict)
        obj.update(
            {
                "version": app_version,
                "debug": debug,
                "manager": CommandManager(debug),
                "today": datetime.now(),
            }
        )

    return app
