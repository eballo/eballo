from datetime import datetime

from click.exceptions import Exit
from typer import Typer, Context, Option

from taskjournal.services.logger import logger


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
    ):
        debug = ctx.obj.get("debug", False)
        custom_date = ctx.obj.get("today")
        m = ctx.obj.get("manager")
        logger.debug(f"date={date!r}, debug={debug},")

        if date:
            try:
                custom_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
            except ValueError:
                logger.error("❌ Invalid date format. Use 'YYYY-MM-DD HH:MM'.")
                raise Exit(code=1)

        m.create_retro(custom_date)

    return app
