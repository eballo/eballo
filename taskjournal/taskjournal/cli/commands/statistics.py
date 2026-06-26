from typing import Any

from rich.console import Console
from rich.panel import Panel
from typer import Typer, Context, Option

from taskjournal.cli.context import get_container, get_manager, get_today, get_debug
from taskjournal.services.logger import logger
from taskjournal.services.working_days import WorkingDaysService  # kept for type hint

console = Console()


def build_app() -> Typer:
    app = Typer(
        help="Statistics command.",
        no_args_is_help=True,
    )

    def get_service(ctx: Context, year: str | None) -> WorkingDaysService:
        debug = get_debug(ctx)
        if not year:
            logger.warning("Getting default year")
            year = str(get_today(ctx).year)
        else:
            logger.debug(f"debug={debug}, year={year}")
        return get_container(ctx).working_days_service(year=year, debug=debug)  # type: ignore[no-any-return]

    common_year_option: Any = Option(
        None, "--year", "-y", help="Year for which to get holidays."
    )

    @app.command(
        "all",
        help="get all working days.\n\nExamples:\n  wk statistics all\n",
    )
    def working_days_summary(
        ctx: Context,
        year: str | None = common_year_option,
    ) -> None:
        get_service(ctx, year).summary()

    @app.command(
        "progress",
        help="get progress.\n\nExamples:\n  wk statistics progress\n",
    )
    def working_days_progress(
        ctx: Context,
        year: str | None = common_year_option,
    ) -> None:
        get_service(ctx, year).get_progress()

    @app.command(
        "real",
        help="get real working days (including holidays).\n\nExamples:\n  wk statistics real\n",
    )
    def working_days_real(
        ctx: Context,
        year: str | None = common_year_option,
    ) -> None:
        get_service(ctx, year).get_real_working_days()

    @app.command(
        "streak",
        help=(
            "Show consecutive journaling streak and all-time record.\n\n"
            "Examples:\n"
            "  wk statistics streak\n"
        ),
    )
    def streak(ctx: Context) -> None:
        today = get_today(ctx)
        stats = get_manager(ctx).get_streak_stats(today)

        console.print(Panel("[bold]Journaling streak[/bold]", expand=False))

        current = stats["current"]
        longest = stats["longest"]
        total = stats["total"]
        ls = stats["longest_start"]
        le = stats["longest_end"]

        current_style = "green" if current >= 5 else "yellow" if current >= 1 else "dim"
        console.print(f"  Current streak   [{current_style}]{current} day{'s' if current != 1 else ''}[/{current_style}]")

        if ls and le and ls != le:
            range_str = f"  [dim]({ls} → {le})[/dim]"
        else:
            range_str = ""
        console.print(f"  Longest streak   [bold]{longest} day{'s' if longest != 1 else ''}[/bold]{range_str}")
        console.print(f"  Total notes      [dim]{total}[/dim]")

    return app
