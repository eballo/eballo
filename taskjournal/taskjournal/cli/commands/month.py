from asyncio import run

from typer import Typer, Context, Option

from taskjournal.cli.context import get_manager, get_today, get_debug, parse_date
from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="Monthly reporting commands.",
        no_args_is_help=True,
    )

    @app.command(
        "report",
        help=(
            "Create a monthly report for the month containing the given date.\n\n"
            "Examples:\n"
            "  wk month report\n"
            "  wk month report --date 2025-08-31\n"
        ),
    )
    def month_report(
        ctx: Context,
        date: str = Option(
            None,
            "--date",
            help="Any date within the target month: 'YYYY-MM-DD'.",
        ),
    ) -> None:
        m = get_manager(ctx)
        custom_date = get_today(ctx)
        logger.debug(f"date={date!r}, debug={get_debug(ctx)}")

        if date:
            custom_date = parse_date(date)

        run(m.create_month_review(custom_date))

    return app
