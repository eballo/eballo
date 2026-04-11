import asyncio
from datetime import datetime

from click.exceptions import Exit
from typer import Typer, Context, Option

from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="Weekly reporting commands.",
        no_args_is_help=True,
    )

    @app.command(
        "report",
        help=(
            "Generate a weekly report for the week containing the given date.\n\n"
            "Examples:\n"
            "  wk week report\n"
            "  wk week report --date 2025-08-31\n"
        ),
    )
    def week_report(
        ctx: Context,
        date: str = Option(
            None,
            "--date",
            help="Any date within the target week: 'YYYY-MM-DD'.",
        ),
    ) -> None:
        debug = ctx.obj.get("debug", False)
        custom_date = ctx.obj.get("today")
        m = ctx.obj.get("manager")
        logger.debug(f"date={date!r}, debug={debug},")

        if date:
            try:
                custom_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                logger.error("❌ Invalid date format. Use 'YYYY-MM-DD'.")
                raise Exit(code=1)

        asyncio.run(m.create_week_summary(custom_date))

    @app.command(
        "recreate-since",
        help=(
            "Recreate all weekly reports from the given date up to today.\n\n"
            "Examples:\n"
            "  wk week recreate-since --date 2026-01-01\n"
        ),
    )
    def recreate_since(
        ctx: Context,
        date: str = Option(
            ...,
            "--date",
            help="Start date to begin recreation: 'YYYY-MM-DD'.",
        ),
    ) -> None:
        m = ctx.obj.get("manager")
        today = ctx.obj.get("today")

        try:
            start_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            logger.error("❌ Invalid date format. Use 'YYYY-MM-DD'.")
            raise Exit(code=1)

        if start_date > today:
            logger.error("❌ Start date cannot be in the future.")
            raise Exit(code=1)

        asyncio.run(m.recreate_week_summaries(start_date, today))

    return app
