from typing import Optional

from typer import Typer, Context, Option

from taskjournal.cli.context import get_manager, get_today, parse_date


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
        today = get_today(ctx)
        if date:
            today = parse_date(date)
        get_manager(ctx).show_info(today)

    return app
