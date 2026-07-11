from datetime import datetime

from rich.panel import Panel
from rich.table import Table
from typer import Context, Option, Typer

from taskjournal.cli.context import get_manager, get_today, parse_date
from taskjournal.services.logger import console, logger

_DATE_FMT = "%Y-%m-%d"
_TIME_FMT = "%H:%M"


def build_app() -> Typer:
    app = Typer(
        help="Manage end-of-day workday alarms.",
        no_args_is_help=True,
    )

    @app.command("list", help="List tracked workday alarms for the past 4 weeks.")
    def alarm_list(ctx: Context) -> None:
        alarms = get_manager(ctx).list_alarms()
        console.print(Panel("[bold]wk alarm list[/bold]", expand=False))
        if not alarms:
            console.print("[dim]No alarm files found in the past 4 weeks.[/dim]")
            return

        table = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 2))
        table.add_column("Date", width=12)
        table.add_column("Time", width=7)
        table.add_column("Message")
        table.add_column("Status", width=10)

        for a in alarms:
            job_id = str(a["job_id"])
            time_str = str(a["scheduled"]) if a["scheduled"] else "[dim]—[/dim]"
            msg = str(a["message"]) if a.get("message") else "[dim]—[/dim]"
            is_past: bool = bool(a["is_past"])
            is_alive: bool = bool(a.get("is_alive", False))

            if is_alive:
                status = "[green]active[/green]"
            elif is_past:
                status = "[dim]expired[/dim]"
            else:
                status = "[yellow]stopped[/yellow]"

            table.add_row(str(a["date"]), time_str, msg, status)

        console.print(table)

    @app.command("cancel", help="Cancel the workday alarm for a given date (or all).")
    def alarm_cancel(
        ctx: Context,
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'. Defaults to today."),
        all_alarms: bool = Option(False, "--all", help="Cancel every tracked alarm (including stale ones)."),
    ) -> None:
        m = get_manager(ctx)

        if all_alarms:
            alarms = m.list_alarms()
            if not alarms:
                console.print("[dim]No alarms to cancel.[/dim]")
                return
            for a in alarms:
                try:
                    d = datetime.strptime(str(a["date"]), _DATE_FMT)
                    m.cancel_alarm_for_date(d)
                except ValueError:
                    pass
        else:
            target = parse_date(date) if date else get_today(ctx)
            if not m.cancel_alarm_for_date(target):
                logger.warning(f"No alarm file found for {target.strftime(_DATE_FMT)}.")

    @app.command("set", help="Set (or reschedule) the workday alarm for a given date and time.")
    def alarm_set(
        ctx: Context,
        time: str = Option(..., "--time", "-t", help="Alarm time: 'HH:MM'."),
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'. Defaults to today."),
        message: str = Option("Time to wrap up!", "--message", "-m", help="Custom reminder message."),
    ) -> None:
        m = get_manager(ctx)
        target = parse_date(date) if date else get_today(ctx)
        try:
            t = datetime.strptime(time, _TIME_FMT)
        except ValueError:
            logger.error(f"Invalid time format '{time}' — expected HH:MM.")
            return
        alarm_time = target.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        m.set_alarm(target, alarm_time, message)

    return app
