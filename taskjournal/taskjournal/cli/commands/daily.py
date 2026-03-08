import asyncio
from datetime import datetime

from click.exceptions import Exit
from typer import Typer, Context, Option

from taskjournal.services.logger import logger


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
        debug = ctx.obj.get("debug", False)
        creation_date = ctx.obj.get("today")
        m = ctx.obj.get("manager")
        logger.debug(f"date={date!r}, force={force}, debug={debug}")

        if force:
            logger.warning(
                "Force option is enabled. Existing daily notes file will be overwritten."
            )

        if date:
            try:
                creation_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
            except ValueError:
                logger.error("❌ Invalid date format. Use 'YYYY-MM-DD HH:MM'.")
                raise Exit(code=1)

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
        debug = ctx.obj.get("debug", False)
        custom_date = ctx.obj.get("today")
        m = ctx.obj.get("manager")

        logger.debug(f"date={date!r}, debug={debug}")

        if date:
            try:
                custom_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
            except ValueError:
                logger.error("❌ Invalid date format. Use 'YYYY-MM-DD HH:MM'.")
                raise Exit(code=1)

        m.finalize_daily_notes(custom_date)

    @app.command(
        "time",
        help="Calculates the time spent until now",
    )
    def daily_time(
        ctx: Context,
    ) -> None:
        debug = ctx.obj.get("debug", False)
        custom_date = ctx.obj.get("today")
        m = ctx.obj.get("manager")

        logger.debug(f"debug={debug}")

        m.daily_time(custom_date)

    return app
