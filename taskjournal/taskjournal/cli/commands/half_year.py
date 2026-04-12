import asyncio

from typer import Typer, Context

from taskjournal.cli.context import get_manager, get_today, get_debug
from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="Half-year reporting commands.",
        no_args_is_help=True,
    )

    @app.command(
        "report",
        help="Create a half-year report\n Examples:\n wk half-year report",
    )
    def half_year_report(
        ctx: Context,
    ) -> None:
        logger.debug(f"debug={get_debug(ctx)}")
        asyncio.run(get_manager(ctx).create_half_year_review(get_today(ctx)))

    return app
