from typer import Typer, Context, Option

from taskjournal.cli.context import get_manager, get_today, get_debug, parse_date
from taskjournal.services.logger import logger

_DATETIME_FMT = "%Y-%m-%d %H:%M"


def build_app() -> Typer:
    app = Typer(
        help="Create a Retrospective",
        no_args_is_help=True,
    )

    @app.command(
        "create",
        help=(
            "Create or open a retrospective file for the current (or configured) period.\n\n"
            "Examples:\n"
            "  wk retro\n"
        ),
    )
    def retro(
        ctx: Context,
        date: str = Option(
            None,
            "--date",
            help="Any date within the target week: 'YYYY-MM-DD'.",
        ),
    ) -> None:
        m = get_manager(ctx)
        custom_date = get_today(ctx)
        logger.debug(f"date={date!r}, debug={get_debug(ctx)}")

        if date:
            custom_date = parse_date(date, _DATETIME_FMT)

        m.create_retro(custom_date)

    return app
