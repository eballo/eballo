from datetime import datetime

from rich.table import Table
from typer import Argument, Option, Typer, Context

from taskjournal.cli.context import get_today
from taskjournal.services.calendar.fireman import FiremanService
from taskjournal.services.logger import console, logger


def build_app() -> Typer:
    app = Typer(
        help="Fireman weeks command.",
        no_args_is_help=True,
    )

    def get_service(ctx: Context, year: int | None = None) -> FiremanService:
        today = get_today(ctx)
        ref = datetime(year, 1, 1) if year else today
        return FiremanService(create_datetime=ref)

    common_year_option = Option(None, "--year", "-y", help="Year (default: current).")

    @app.command("add", help="Register a fireman week (any date within that week).")
    def fireman_add(
        ctx: Context,
        date: str = Argument(..., help="Any date within the fireman week (YYYY-MM-DD)."),
    ) -> None:
        get_service(ctx).add_week(date)

    @app.command("list", help="List all fireman weeks for a year.")
    def fireman_list(
        ctx: Context,
        year: int | None = common_year_option,
    ) -> None:
        today = get_today(ctx).date()
        svc = get_service(ctx, year)
        weeks = svc.get_all_weeks()

        if not weeks:
            console.print("No fireman weeks registered.")
            return

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("status", width=4)
        table.add_column("week")

        current_monday = svc._get_monday(today)
        for monday in weeks:
            if monday < current_monday:
                icon = "[dim]✓[/dim]"
                label = f"[dim]week of {monday}[/dim]"
            elif monday == current_monday:
                icon = "[bold yellow]▶[/bold yellow]"
                label = f"[bold yellow]week of {monday} ← this week[/bold yellow]"
            else:
                icon = "[cyan]○[/cyan]"
                label = f"week of {monday}"
            table.add_row(icon, label)

        console.print(table)

    @app.command("upcoming", help="Show upcoming fireman weeks.")
    def fireman_upcoming(
        ctx: Context,
        year: int | None = common_year_option,
    ) -> None:
        today = get_today(ctx).date()
        svc = get_service(ctx, year)
        weeks = svc.get_upcoming_weeks(today)

        if not weeks:
            console.print("No upcoming fireman weeks.")
            return

        current_monday = svc._get_monday(today)
        for monday in weeks:
            days = (monday - today).days
            if monday == current_monday:
                console.print(f"[bold yellow]▶[/bold yellow] week of {monday} — this week")
            else:
                console.print(f"[cyan]○[/cyan] week of {monday} — in {days} day(s)")

    @app.command("summary", help="Summary of fireman weeks (done, remaining, next).")
    def fireman_summary(
        ctx: Context,
        year: int | None = common_year_option,
    ) -> None:
        today = get_today(ctx).date()
        get_service(ctx, year).summary(today)

    return app
