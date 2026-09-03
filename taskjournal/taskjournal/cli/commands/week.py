from asyncio import run
from datetime import timedelta
from os.path import exists, join

from sys import exit as sys_exit
from rich.panel import Panel
from rich.table import Table
from typer import Typer, Context, Option

from taskjournal.cli.context import get_manager, get_today, get_debug, parse_date
from taskjournal.services.file import FileService
from taskjournal.services.logger import console, logger
from taskjournal.services.time import TimeService


def build_app() -> Typer:
    app = Typer(
        help="Weekly reporting commands.",
        no_args_is_help=True,
        pretty_exceptions_enable=False,
    )

    @app.command(
        "report",
        help=(
            "Generate a weekly report for the week containing the given date.\n\n"
            "Examples:\n"
            "  wk week report\n"
            "  wk week report --date 2025-08-31\n"
            "  wk week report --tickets\n"
        ),
    )
    def week_report(
        ctx: Context,
        date: str = Option(
            None,
            "--date",
            help="Any date within the target week: 'YYYY-MM-DD'.",
        ),
        tickets: bool = Option(
            False,
            "--tickets",
            help="Add a section grouping the week's Jira tickets by status.",
        ),
    ) -> None:
        m = get_manager(ctx)
        custom_date = get_today(ctx)
        logger.debug(f"date={date!r}, tickets={tickets}, debug={get_debug(ctx)}")

        if date:
            custom_date = parse_date(date)

        run(m.create_week_summary(custom_date, tickets=tickets))

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
        m = get_manager(ctx)
        today = get_today(ctx)
        start_date = parse_date(date)

        if start_date > today:
            logger.error("❌ Start date cannot be in the future.")
            sys_exit(1)

        run(m.recreate_week_summaries(start_date, today))

    @app.command(
        "list",
        help=(
            "List daily notes for a week with their status and time worked.\n\n"
            "Examples:\n"
            "  wk week list\n"
            "  wk week list --date 2026-06-01\n"
        ),
    )
    def week_list(
        ctx: Context,
        date: str | None = Option(None, "--date", help="Any date within the target week: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        manager = get_manager(ctx)

        # Monday of the target week
        monday = today - timedelta(days=today.weekday())
        week_folder, _ = TimeService.get_week_folder_and_daily_notes_file(monday)

        week_label = f"{monday.strftime('%Y-%m-%d')} → {(monday + timedelta(days=4)).strftime('%Y-%m-%d')}"
        console.print(Panel(f"[bold]Week {monday.strftime('%W')}[/bold]  {week_label}", expand=False))

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Day", style="bold", width=10)
        table.add_column("Date", width=12)
        table.add_column("Status", width=14)
        table.add_column("Time")

        total_seconds = 0

        for i in range(5):
            day = monday + timedelta(days=i)
            day_name = day.strftime("%A")[:3]
            date_str = day.strftime("%Y-%m-%d")
            daily_file = join(week_folder, manager.time_service.get_daily_notes_name(day))

            if not exists(daily_file):
                table.add_row(day_name, date_str, "[dim]— missing[/dim]", "")
                continue

            finalized = FileService.check_finalized_in_file(daily_file)

            try:
                _, elapsed_hours, _ = TimeService.calculate_working_hours(daily_file)
                if elapsed_hours:
                    secs = int(elapsed_hours * 3600)
                    total_seconds += secs
                    h, m = TimeService.seconds_to_hours_minutes(secs)
                    time_str = f"{h}h {m:02d}m"
                else:
                    time_str = ""
            except Exception:
                time_str = ""

            if finalized:
                status_str = "[green]✓ finalized[/green]"
            else:
                status_str = "[yellow]○ open[/yellow]"

            table.add_row(day_name, date_str, status_str, time_str)

        console.print(table)

        if total_seconds:
            h, m = TimeService.seconds_to_hours_minutes(total_seconds)
            console.print(f"\n[dim]Total:[/dim]  {h}h {m:02d}m")

    return app
