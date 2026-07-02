from typing import Any

from rich.panel import Panel
from rich.table import Table
from typer import Typer, Context, Option

from taskjournal.cli.context import get_container, get_manager, get_today, get_debug
from taskjournal.services.logger import console, logger
from taskjournal.services.calendar.working_days import WorkingDaysService  # kept for type hint
from taskjournal.services.time import TimeService


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

    @app.command(
        "completion",
        help="Show daily task completion rate over time.\n\nExamples:\n  wk statistics completion\n  wk statistics completion --year 2025\n",
    )
    def completion(
        ctx: Context,
        year: int | None = Option(None, "--year", "-y", help="Year to analyse (default: current)."),
    ) -> None:
        today = get_today(ctx)
        target_year = year or today.year
        data = get_manager(ctx).get_completion_stats(target_year)

        if not data:
            logger.warning(f"No daily notes found for {target_year}.")
            return

        console.print(Panel(f"[bold]Task completion[/bold] — {target_year}", expand=False))

        total_done = sum(d for _, d, _ in data)
        total_tasks = sum(t for _, _, t in data)
        avg_rate = round(total_done / total_tasks * 100) if total_tasks else 0

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Date", style="dim", width=12)
        table.add_column("Done", width=6)
        table.add_column("Total", width=6)
        table.add_column("Rate", width=8)
        table.add_column("Bar", min_width=20)

        for date_str, done, total in data[-30:]:
            rate = round(done / total * 100) if total else 0
            bar_filled = rate // 5
            bar = "[green]" + "█" * bar_filled + "[/green]" + "░" * (20 - bar_filled)
            style = "green" if rate >= 80 else "yellow" if rate >= 50 else "red"
            table.add_row(date_str, str(done), str(total), f"[{style}]{rate}%[/{style}]", bar)

        console.print(table)
        console.print(f"\n  Average completion rate: [bold]{avg_rate}%[/bold]  ({total_done}/{total_tasks} tasks over {len(data)} days)")

    @app.command(
        "workload",
        help="Show hours worked per week.\n\nExamples:\n  wk statistics workload\n  wk statistics workload --year 2025\n",
    )
    def workload(
        ctx: Context,
        year: int | None = Option(None, "--year", "-y", help="Year to analyse (default: current)."),
        threshold: int = Option(45, "--threshold", help="Hours/week considered overload."),
    ) -> None:
        today = get_today(ctx)
        target_year = year or today.year
        data = get_manager(ctx).get_workload_stats(target_year)

        if not data:
            logger.warning(f"No workload data found for {target_year}.")
            return

        console.print(Panel(f"[bold]Weekly workload[/bold] — {target_year}", expand=False))

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Week", style="bold", width=6)
        table.add_column("Hours", width=8)
        table.add_column("Bar", min_width=20)
        table.add_column("Flag", width=4)

        for week, seconds in data:
            h, m = TimeService.seconds_to_hours_minutes(seconds)
            total_h = h + m / 60
            bar_len = min(int(total_h), 50)
            bar = "█" * bar_len
            overload = total_h >= threshold
            bar_color = "red" if overload else "green"
            flag = "⚠" if overload else ""
            table.add_row(week, f"{h}h {m:02d}m", f"[{bar_color}]{bar}[/{bar_color}]", f"[yellow]{flag}[/yellow]")

        console.print(table)

    @app.command(
        "patterns",
        help="Show productivity patterns: best day, carry-over rate, avg tasks.\n\nExamples:\n  wk statistics patterns\n  wk statistics patterns --year 2025\n",
    )
    def patterns(
        ctx: Context,
        year: int | None = Option(None, "--year", "-y", help="Year to analyse (default: current)."),
    ) -> None:
        today = get_today(ctx)
        target_year = year or today.year
        stats = get_manager(ctx).get_pattern_stats(target_year)

        console.print(Panel(f"[bold]Productivity patterns[/bold] — {target_year}", expand=False))

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("label", style="dim", width=26)
        table.add_column("value")

        if stats["best_day"]:
            table.add_row("Most productive day", f"[bold]{stats['best_day']}[/bold]")
        if stats["best_hour"] is not None:
            table.add_row("Most productive start hour", f"[bold]{stats['best_hour']}:00[/bold]")
        table.add_row("Avg tasks completed/day", f"[bold]{stats['avg_done_per_day']}[/bold]")
        table.add_row("Carry-over rate", f"[bold]{stats['carry_over_rate']}%[/bold]  [dim](tasks repeated 2+ days)[/dim]")

        console.print(table)

        avg_by_day: dict[str, float] = stats["avg_by_day"]  # type: ignore[assignment]
        if avg_by_day:
            console.print()
            console.print("  [dim]Average tasks done by day of week:[/dim]")
            for day_name, avg in avg_by_day.items():
                bar = "█" * int(avg)
                console.print(f"  {day_name:<12} {avg:>4}  [cyan]{bar}[/cyan]")

    @app.command(
        "tags",
        help="Show days worked per epic tag.\n\nExamples:\n  wk statistics tags\n  wk statistics tags --year 2025\n",
    )
    def tags(
        ctx: Context,
        year: int | None = Option(None, "--year", "-y", help="Year to analyse (default: current)."),
    ) -> None:
        today = get_today(ctx)
        target_year = year or today.year
        data = get_manager(ctx).get_tags_stats(target_year)

        if not data:
            logger.warning(f"No epic tags found for {target_year}. Start daily notes with Jira connected to fetch epics.")
            return

        console.print(Panel(f"[bold]Days per epic tag[/bold] — {target_year}", expand=False))

        max_days = data[0][1] if data else 1
        for tag, days in data:
            bar_len = max(1, round(days / max_days * 30))
            bar = "█" * bar_len
            console.print(f"  {tag:<40} {days:>3}d  [cyan]{bar}[/cyan]")

    return app
