from sys import exit as sys_exit

from rich.table import Table
from typer import Argument, Context, Option, Typer

from taskjournal.cli.context import get_manager, get_today, parse_date
from taskjournal.models.task import Status
from taskjournal.services.logger import console, logger


def build_app() -> Typer:
    app = Typer(
        help="Manage tasks in the current day's notes.",
        no_args_is_help=True,
        pretty_exceptions_enable=False,
    )

    @app.command("list", help="List all tasks for today (or a given date).")
    def task_list(
        ctx: Context,
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        tasks = get_manager(ctx).list_tasks_in_daily(today)

        if not tasks:
            console.print("No tasks found.")
            return

        _STATUS_STYLE: dict[str, tuple[str, str, str]] = {
            "Done":        ("[green]✓[/green]",    "[green]done[/green]",          "[dim]{desc}[/dim]"),
            "Blocked":     ("[red]✗[/red]",         "[bold red]blocked[/bold red]", "[bold red]{desc}[/bold red]"),
            "In Progress": ("[blue]▶[/blue]",       "[blue]wip[/blue]",             "{desc}"),
            "Code Review": ("[cyan]~[/cyan]",       "[cyan]review[/cyan]",          "[cyan]{desc}[/cyan]"),
        }
        _DEFAULT_STYLE: tuple[str, str, str] = ("[dim]○[/dim]", "[dim]todo[/dim]", "[dim]{desc}[/dim]")

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("icon", width=4)
        table.add_column("status", width=9)
        table.add_column("task")

        for t in tasks:
            icon, badge, desc_fmt = _STATUS_STYLE.get(t.status.value, _DEFAULT_STYLE)
            table.add_row(icon, badge, desc_fmt.format(desc=t.description))
        console.print(table)

    @app.command("add", help="Add a new task to today's planned tasks.")
    def task_add(
        ctx: Context,
        description: str = Argument(..., help="Task description."),
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        try:
            get_manager(ctx).add_task_to_daily(today, description)
            console.print(f"[green]✓[/green] Added: {description}")
        except (FileNotFoundError, ValueError) as e:
            logger.error(str(e))
            sys_exit(1)

    @app.command("done", help="Mark a task as done in today's notes.")
    def task_done(
        ctx: Context,
        description: str = Argument(..., help="Task description (partial match)."),
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        try:
            found = get_manager(ctx).complete_task_in_daily(today, description)
            if found:
                console.print(f"[green]✓[/green] Marked done: {description}")
            else:
                logger.warning(f"No matching task found for: {description}")
        except FileNotFoundError as e:
            logger.error(str(e))
            sys_exit(1)

    @app.command("block", help="Mark a task as blocked in today's notes.")
    def task_block(
        ctx: Context,
        description: str = Argument(..., help="Task description (partial match)."),
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        try:
            found = get_manager(ctx).block_task_in_daily(today, description)
            if found:
                console.print(f"[yellow]⚠[/yellow] Marked blocked: {description}")
            else:
                logger.warning(f"No matching task found for: {description}")
        except FileNotFoundError as e:
            logger.error(str(e))
            sys_exit(1)

    @app.command("wip", help="Mark a task as work in progress in today's notes.")
    def task_wip(
        ctx: Context,
        description: str = Argument(..., help="Task description (partial match)."),
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        try:
            found = get_manager(ctx).wip_task_in_daily(today, description)
            if found:
                console.print(f"[blue]▶[/blue] Marked wip: {description}")
            else:
                logger.warning(f"No matching task found for: {description}")
        except FileNotFoundError as e:
            logger.error(str(e))
            sys_exit(1)

    return app
