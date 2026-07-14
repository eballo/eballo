from asyncio import run
from sys import exit as sys_exit

from rich.table import Table
from typer import Argument, Context, Option, Typer

from taskjournal.cli.context import get_manager, get_today, parse_date
from taskjournal.models.task import Status
from taskjournal.services.logger import console, logger

_DOW_CHOICES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


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

    @app.command(
        "sync",
        help=(
            "Check your active Jira task and code-review tasks against today's "
            "notes: add whichever are missing, and correct the status of any "
            "that have gone stale (e.g. a code-review approval).\n\n"
            "Examples:\n"
            "  wk task sync\n"
            "  wk task sync --date 2026-06-25\n"
        ),
    )
    def task_sync(
        ctx: Context,
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        try:
            run(get_manager(ctx).sync_tasks(today))
        except (FileNotFoundError, ValueError) as e:
            logger.error(str(e))
            sys_exit(1)

    # ── Recurring tasks ───────────────────────────────────────────────────────

    recurring = Typer(
        name="recurring",
        help="Manage recurring tasks injected automatically into daily notes.",
        no_args_is_help=True,
    )
    app.add_typer(recurring, name="recurring")

    @recurring.command(
        "add",
        help=(
            "Add or update a recurring task.\n\nExamples:\n"
            "  wk task recurring add 'Check alerts'\n"
            "  wk task recurring add 'Standup' --every monday,wednesday,friday\n"
            "  wk task recurring add 'Deel monthly report' --monthly\n"
        ),
    )
    def recurring_add(
        ctx: Context,
        description: str = Argument(..., help="Task description."),
        every: str | None = Option(
            None,
            "--every",
            help="Comma-separated weekday names (e.g. 'monday,friday') or omit for every day.",
        ),
        monthly: bool = Option(
            False,
            "--monthly",
            help="Inject on the first workday of each month.",
        ),
    ) -> None:
        if monthly and every:
            logger.error("Cannot use --monthly together with --every.")
            sys_exit(1)
        days: list[str] | None = None
        if every:
            days = [d.strip().lower() for d in every.split(",")]
            invalid = [d for d in days if d not in _DOW_CHOICES]
            if invalid:
                logger.error(f"Unknown days: {', '.join(invalid)}. Valid: {', '.join(_DOW_CHOICES)}")
                sys_exit(1)
        try:
            get_manager(ctx).add_recurring_task(description, days, monthly)
            if monthly:
                when = "first workday of each month"
            elif every:
                when = f"every {every}"
            else:
                when = "every day"
            console.print(f"[green]✓[/green] Recurring task added ({when}): {description}")
        except ValueError as e:
            logger.error(str(e))
            sys_exit(1)

    @recurring.command("list", help="List all recurring tasks.")
    def recurring_list(ctx: Context) -> None:
        tasks = get_manager(ctx).list_recurring_tasks()
        if not tasks:
            console.print("[dim]No recurring tasks configured.[/dim]")
            return

        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
        table.add_column("Description")
        table.add_column("When", style="dim", width=30)

        for t in tasks:
            days = t.get("days", "every")
            if days == "every":
                when = "every day"
            elif days == "monthly_first_workday":
                when = "first workday of each month"
            else:
                when = ", ".join(days)  # type: ignore[arg-type]
            table.add_row(str(t.get("description", "")), when)

        console.print(table)

    @recurring.command("remove", help="Remove a recurring task by description.")
    def recurring_remove(
        ctx: Context,
        description: str = Argument(..., help="Exact task description to remove."),
    ) -> None:
        found = get_manager(ctx).remove_recurring_task(description)
        if found:
            console.print(f"[green]✓[/green] Removed recurring task: {description}")
        else:
            logger.warning(f"No recurring task found with description: {description!r}")
            sys_exit(1)

    return app
