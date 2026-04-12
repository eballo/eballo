import asyncio

from click.exceptions import Exit
from typer import Typer, Context, Option

from taskjournal.cli.context import get_manager, get_today, get_debug, parse_date
from taskjournal.services.logger import logger

_DATETIME_FMT = "%Y-%m-%d %H:%M"


def build_app() -> Typer:
    app = Typer(
        help="Daily workflow commands (start, finish).",
        no_args_is_help=True,
    )

    @app.command(
        "start",
        help=(
            "Create (or overwrite with --force) the daily notes file for the given date.\n\n"
            "Examples:\n"
            "  wk daily start\n"
            "  wk daily start --date '2025-09-02 09:00' --force\n"
        ),
    )
    def daily_start(
        ctx: Context,
        date: str = Option(
            None,
            "--date",
            help="Target date/time: 'today' or 'YYYY-MM-DD HH:MM'.",
        ),
        force: bool = Option(
            False,
            "--force",
            help="Overwrite the daily notes file if it already exists.",
            show_default=True,
        ),
        firefighter: bool = Option(
            False,
            "--ff",
            help="Firefighter mode True/False",
            show_default=True,
        ),
        work_from: str = Option(
            None,
            "--w",
            help="Specify the working place (Home, Office)",
            show_default=True,
        ),
    ) -> None:
        m = get_manager(ctx)
        creation_date = get_today(ctx)
        logger.debug(f"date={date!r}, force={force}, debug={get_debug(ctx)}")

        if force:
            logger.warning(
                "Force option is enabled. Existing daily notes file will be overwritten."
            )

        if date:
            creation_date = parse_date(date, _DATETIME_FMT)

        asyncio.run(m.create_daily_notes(creation_date, force, firefighter, work_from))

    @app.command(
        "finish",
        help=(
            "Finalize the daily notes (write end time, totals, prompt for summary).\n\n"
            "Examples:\n"
            "  wk daily finish\n"
            "  wk daily finish --date '2025-09-02 17:30'\n"
            "  wk daily finish --force\n"
        ),
    )
    def daily_finish(
        ctx: Context,
        date: str = Option(
            None,
            "--date",
            help="Target date/time: 'today' or 'YYYY-MM-DD HH:MM'. (works as a date override if already exists)",
        ),
    ) -> None:
        m = get_manager(ctx)
        custom_date = get_today(ctx)
        logger.debug(f"date={date!r}, debug={get_debug(ctx)}")

        if date:
            custom_date = parse_date(date, _DATETIME_FMT)

        m.finalize_daily_notes(custom_date)

    @app.command(
        "time",
        help="Calculates the time spent until now",
    )
    def daily_time(
        ctx: Context,
    ) -> None:
        logger.debug(f"debug={get_debug(ctx)}")
        get_manager(ctx).daily_time(get_today(ctx))

    return app
