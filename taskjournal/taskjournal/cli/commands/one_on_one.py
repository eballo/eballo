from typer import Typer, Context

from taskjournal.cli.context import get_manager, get_today, get_debug
from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="1on1 reporting commands.",
        no_args_is_help=True,
    )

    @app.command(
        "report",
        help="Create a 1on1 report .\n\n Examples:\n wk 1on1 report\n",
    )
    def one_on_one_report(
        ctx: Context,
    ) -> None:
        logger.debug(f"debug={get_debug(ctx)}")
        get_manager(ctx).create_one_on_one(get_today(ctx))

    return app
