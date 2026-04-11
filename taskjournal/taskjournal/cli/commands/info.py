from datetime import datetime
from typing import Optional

from typer import Typer, Context, Option

from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="General information commands.",
        no_args_is_help=True,
    )

    @app.command(
        "show",
        help=(
            "Show current day and week number.\n\n"
            "Examples:\n"
            "  wk info show\n"
            "  wk info show --date 2025-08-31\n"
        ),
    )
    def show(
        ctx: Context,
        date: Optional[str] = Option(
            None,
            "--date",
            help="Show info for a specific date: 'YYYY-MM-DD'.",
        ),
    ) -> None:
        m = ctx.obj.get("manager")
        today = ctx.obj.get("today")

        if date:
            try:
                today = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                logger.error("❌ Invalid date format. Use 'YYYY-MM-DD'.")
                return

        m.show_info(today)

    return app
