from asyncio import run
from datetime import datetime
from os import environ
from os.path import exists
from subprocess import run as subprocess_run
from sys import exit as sys_exit
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typer import Argument, Context, Option, Typer

from taskjournal.cli.context import get_debug, get_manager, get_today, parse_date
from taskjournal.config import EDITOR_APP
from taskjournal.models.task import Status
from taskjournal.services.file import FileService
from taskjournal.services.logger import logger
from taskjournal.services.time import TimeService

_DATETIME_FMT = "%Y-%m-%d %H:%M"

console = Console()


def _fix_file_interactively(manager: Any, date_str: str, file_path: str, issues: list[str]) -> None:
    if "missing end time" in issues:
        raw = input("  End time (HH:MM, blank to skip): ").strip()
        if raw:
            try:
                t = datetime.strptime(raw, "%H:%M")
            except ValueError:
                console.print("  [red]✗ Invalid format (expected HH:MM), skipping[/red]")
            else:
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                end_dt = file_date.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
                try:
                    manager.fix_end_time_and_time_spent(file_path, end_dt)
                    console.print("  [green]✓ End time set and time spent calculated[/green]")
                except ValueError as e:
                    console.print(f"  [red]✗ {e}[/red]")
    elif "missing time spent" in issues:
        if not manager.fix_time_spent_from_file(file_path):
            raw = input("  End time (HH:MM, blank to skip): ").strip()
            if raw:
                try:
                    t = datetime.strptime(raw, "%H:%M")
                except ValueError:
                    console.print("  [red]✗ Invalid format (expected HH:MM), skipping[/red]")
                else:
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    end_dt = file_date.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
                    try:
                        manager.fix_end_time_and_time_spent(file_path, end_dt)
                        console.print("  [green]✓ End time set and time spent calculated[/green]")
                    except ValueError as e:
                        console.print(f"  [red]✗ {e}[/red]")
        else:
            console.print("  [green]✓ Time spent calculated from existing times[/green]")

    if "missing summary" in issues:
        raw = input("  Summary (blank to skip): ").strip()
        if raw:
            manager.fix_summary(file_path, raw)
            console.print("  [green]✓ Summary saved[/green]")


def build_app() -> Typer:
    app = Typer(
        help="Daily workflow commands (start, finish, status, check).",
        no_args_is_help=True,
        pretty_exceptions_enable=False,
    )

    @app.command(
        "start",
        help=(
            "Create (or overwrite with --force) the daily notes file for the given date.\n\n"
            "Examples:\n"
            "  wk daily start\n"
            "  wk daily start --date '2025-09-02 09:00' --force\n"
        ),
    )
    def daily_start(
        ctx: Context,
        date: str = Option(
            None,
            "--date",
            help="Target date/time: 'today' or 'YYYY-MM-DD HH:MM'.",
        ),
        force: bool = Option(
            False,
            "--force",
            help="Overwrite the daily notes file if it already exists.",
            show_default=True,
        ),
        firefighter: bool = Option(
            False,
            "--ff",
            help="Firefighter mode True/False",
            show_default=True,
        ),
        work_from: str = Option(
            None,
            "--w",
            help="Specify the working place (Home, Office)",
            show_default=True,
        ),
        offline: bool = Option(
            False,
            "--offline",
            help="Skip all Jira and GitHub calls (no internet required).",
            show_default=True,
        ),
    ) -> None:
        m = get_manager(ctx)
        creation_date = get_today(ctx)
        logger.debug(f"date={date!r}, force={force}, offline={offline}, debug={get_debug(ctx)}")

        if force:
            logger.warning(
                "Force option is enabled. Existing daily notes file will be overwritten."
            )

        if date:
            creation_date = parse_date(date, _DATETIME_FMT)

        prev = m.get_previous_day_issues(creation_date)
        if prev:
            prev_date_str, prev_file, prev_issues = prev
            logger.warning(
                f"Previous day's note ({prev_date_str}) is incomplete: {', '.join(prev_issues)}"
            )
            answer = input("Fix it now? [y/N]: ").strip().lower()
            if answer == "y":
                console.print(f"\n[bold cyan]{prev_date_str}[/bold cyan]  [yellow]{' · '.join(prev_issues)}[/yellow]")
                _fix_file_interactively(m, prev_date_str, prev_file, prev_issues)
                console.print()

        run(m.create_daily_notes(creation_date, force, firefighter, work_from, offline))

    @app.command(
        "finish",
        help=(
            "Finalize the daily notes (write end time, totals, prompt for summary).\n\n"
            "Examples:\n"
            "  wk daily finish\n"
            "  wk daily finish --date '2025-09-02 17:30'\n"
        ),
    )
    def daily_finish(
        ctx: Context,
        date: str = Option(
            None,
            "--date",
            help="Target date/time: 'today' or 'YYYY-MM-DD HH:MM'.",
        ),
    ) -> None:
        m = get_manager(ctx)
        custom_date = get_today(ctx)
        logger.debug(f"date={date!r}, debug={get_debug(ctx)}")

        if date:
            custom_date = parse_date(date, _DATETIME_FMT)

        m.finalize_daily_notes(custom_date)

    @app.command(
        "time",
        help="Show elapsed working time for today.",
    )
    def daily_time(ctx: Context) -> None:
        logger.debug(f"debug={get_debug(ctx)}")
        get_manager(ctx).daily_time(get_today(ctx))

    @app.command(
        "status",
        help=(
            "Show a summary of the current day: elapsed time, task breakdown, and finalization state.\n\n"
            "Examples:\n"
            "  wk daily status\n"
            "  wk daily status --date 2026-06-25\n"
        ),
    )
    def daily_status(
        ctx: Context,
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        daily_file, _ = TimeService.resolve_daily_notes_file(today)

        if not exists(daily_file):
            logger.error(f"No daily notes found for {today.strftime('%Y-%m-%d')}.")
            sys_exit(1)

        # Timing
        started, elapsed_hours, finish_time = TimeService.calculate_working_hours(daily_file)

        # Tasks
        manager = get_manager(ctx)
        data = manager.parser.parse(daily_file)
        tasks = data.get("planned_tasks", []) if data else []
        done = sum(1 for t in tasks if t.status == Status.DONE)
        pending = sum(1 for t in tasks if t.status == Status.TODO)
        blocked = sum(1 for t in tasks if t.status == Status.BLOCKED)

        finalized = FileService.check_finalized_in_file(daily_file)

        # Display
        day_label = today.strftime("%A, %Y-%m-%d")
        state_label = "[dim]Finalized[/dim]" if finalized else "[yellow]Open — not finalized[/yellow]"

        console.print(Panel(f"[bold]{day_label}[/bold]  {state_label}", expand=False))

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("label", style="dim", width=18)
        table.add_column("value")

        if started:
            table.add_row("Started", started.strftime("%H:%M"))
        if elapsed_hours is not None:
            h, m = TimeService.seconds_to_hours_minutes(int(elapsed_hours * 3600))
            table.add_row("Elapsed", f"{h}h {m:02d}m")
        if finish_time:
            table.add_row("Est. finish", finish_time.strftime("%H:%M"))

        table.add_row("", "")
        task_parts = [f"[green]✓ {done} done[/green]"]
        if pending:
            task_parts.append(f"[yellow]○ {pending} pending[/yellow]")
        if blocked:
            task_parts.append(f"[red]✗ {blocked} blocked[/red]")
        table.add_row("Tasks", "  ·  ".join(task_parts) if tasks else "[dim]none[/dim]")

        console.print(table)

    @app.command(
        "check",
        help=(
            "Validate the structure of today's daily notes file.\n\n"
            "Examples:\n"
            "  wk daily check\n"
            "  wk daily check --date 2026-06-25\n"
        ),
    )
    def daily_check(
        ctx: Context,
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        daily_file, _ = TimeService.resolve_daily_notes_file(today)

        console.print(
            Panel(
                f"[bold]Daily check[/bold] — {today.strftime('%Y-%m-%d')}",
                expand=False,
            )
        )

        if not exists(daily_file):
            logger.error(f"No daily notes found for {today.strftime('%Y-%m-%d')}.")
            sys_exit(1)

        checks: list[tuple[bool, str, str]] = []  # (ok, label, detail)

        # Start time
        try:
            lines = FileService.get_lines(daily_file)
            _, start_time = TimeService.get_start_time(lines)
            checks.append((True, "Start time", start_time.strftime("%H:%M:%S")))
        except ValueError:
            checks.append((False, "Start time", "Missing"))

        # Finalized (end time present)
        finalized = FileService.check_finalized_in_file(daily_file)
        checks.append((
            finalized,
            "End time",
            "Present" if finalized else "Missing — run wk daily finish",
        ))

        # Tasks
        manager = get_manager(ctx)
        data = manager.parser.parse(daily_file)
        tasks = data.get("planned_tasks", []) if data else []
        if tasks:
            done = sum(1 for t in tasks if t.status == Status.DONE)
            pending = sum(1 for t in tasks if t.status == Status.TODO)
            blocked = sum(1 for t in tasks if t.status == Status.BLOCKED)
            checks.append((True, "Tasks", f"{len(tasks)} found  ({done} done · {pending} pending · {blocked} blocked)"))
        else:
            checks.append((False, "Tasks", "No tasks found"))

        # Summary
        summary_lines = data.get("summary", []) if data else []
        has_summary = any(line.strip() for line in summary_lines)
        checks.append((
            has_summary,
            "Summary",
            "Present" if has_summary else "Empty — add a daily summary before finishing",
        ))

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("icon", width=3)
        table.add_column("label", style="bold", width=14)
        table.add_column("detail")

        issues = 0
        for ok, label, detail in checks:
            icon = "[green]✓[/green]" if ok else "[yellow]⚠[/yellow]"
            style = "green" if ok else "yellow"
            table.add_row(icon, label, f"[{style}]{detail}[/{style}]")
            if not ok:
                issues += 1

        console.print(table)

        if issues == 0:
            logger.info("All checks passed.")
        else:
            logger.warning(f"{issues} issue{'s' if issues > 1 else ''} found.")

    @app.command(
        "sync",
        help=(
            "Pull latest Jira tasks and add any missing ones to today's notes.\n\n"
            "Examples:\n"
            "  wk daily sync\n"
            "  wk daily sync --date 2026-06-25\n"
        ),
    )
    def daily_sync(
        ctx: Context,
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        try:
            run(get_manager(ctx).sync_daily_notes(today))
        except (FileNotFoundError, ValueError) as e:
            logger.error(str(e))
            sys_exit(1)

    # --- task sub-group ---
    task_app = Typer(
        help="Manage tasks in the current day's notes.",
        no_args_is_help=True,
        pretty_exceptions_enable=False,
    )
    app.add_typer(task_app, name="task")

    @task_app.command("list", help="List all tasks for today (or a given date).")
    def task_list(
        ctx: Context,
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        tasks = get_manager(ctx).list_tasks_in_daily(today)

        if not tasks:
            logger.info("No tasks found.")
            return

        _STATUS_STYLE: dict[str, tuple[str, str, str]] = {
            "Done":        ("[green]✓[/green]",    "[green]done[/green]",        "[dim]{desc}[/dim]"),
            "Blocked":     ("[red]✗[/red]",         "[bold red]blocked[/bold red]", "[bold red]{desc}[/bold red]"),
            "In Progress": ("[blue]▶[/blue]",       "[blue]wip[/blue]",           "{desc}"),
            "Code Review": ("[cyan]~[/cyan]",       "[cyan]review[/cyan]",        "[cyan]{desc}[/cyan]"),
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

    @task_app.command("add", help="Add a new task to today's planned tasks.")
    def task_add(
        ctx: Context,
        description: str = Argument(..., help="Task description."),
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        try:
            get_manager(ctx).add_task_to_daily(today, description)
            logger.info(f"Added: {description}")
        except (FileNotFoundError, ValueError) as e:
            logger.error(str(e))
            sys_exit(1)

    @task_app.command("done", help="Mark a task as done in today's notes.")
    def task_done(
        ctx: Context,
        description: str = Argument(..., help="Task description (partial match)."),
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        try:
            found = get_manager(ctx).complete_task_in_daily(today, description)
            if found:
                logger.info(f"Marked done: {description}")
            else:
                logger.warning(f"No matching task found for: {description}")
        except FileNotFoundError as e:
            logger.error(str(e))
            sys_exit(1)

    @task_app.command("block", help="Mark a task as blocked in today's notes.")
    def task_block(
        ctx: Context,
        description: str = Argument(..., help="Task description (partial match)."),
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        try:
            found = get_manager(ctx).block_task_in_daily(today, description)
            if found:
                logger.info(f"Marked blocked: {description}")
            else:
                logger.warning(f"No matching task found for: {description}")
        except FileNotFoundError as e:
            logger.error(str(e))
            sys_exit(1)

    @task_app.command("wip", help="Mark a task as work in progress in today's notes.")
    def task_wip(
        ctx: Context,
        description: str = Argument(..., help="Task description (partial match)."),
        date: str | None = Option(None, "--date", help="Date: 'YYYY-MM-DD'."),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        try:
            found = get_manager(ctx).wip_task_in_daily(today, description)
            if found:
                logger.info(f"Marked wip: {description}")
            else:
                logger.warning(f"No matching task found for: {description}")
        except FileNotFoundError as e:
            logger.error(str(e))
            sys_exit(1)

    @app.command(
        "audit",
        help=(
            "Scan all daily notes for a year and report incomplete ones.\n\n"
            "Examples:\n"
            "  wk daily audit\n"
            "  wk daily audit --year 2025\n"
            "  wk daily audit --fix\n"
        ),
    )
    def daily_audit(
        ctx: Context,
        year: int | None = Option(None, "--year", help="Year to scan (default: current year)."),
        fix: bool = Option(False, "--fix", help="Open each incomplete file in $EDITOR."),
    ) -> None:
        today = get_today(ctx)
        target_year = year or today.year
        manager = get_manager(ctx)

        console.print(Panel(f"[bold]wk daily audit[/bold] — {target_year}", expand=False))

        results = manager.audit_daily_notes(target_year)

        if not results:
            logger.warning(f"No daily notes found for {target_year}.")
            sys_exit(0)

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("icon", width=3)
        table.add_column("date", style="bold", width=12)
        table.add_column("issues")

        ok_count = issue_count = 0
        files_to_fix: list[str] = []

        for date_str, file_path, issues in results:
            if issues:
                table.add_row(
                    "[yellow]⚠[/yellow]",
                    date_str,
                    f"[yellow]{' · '.join(issues)}[/yellow]",
                )
                files_to_fix.append(file_path)
                issue_count += 1
            else:
                ok_count += 1

        console.print(table)

        summary = f"{ok_count} OK"
        if issue_count:
            summary += f"  /  {issue_count} with issues"
        summary += f"  ({ok_count + issue_count} total)"
        logger.info(summary)

        if fix and files_to_fix:
            console.print()
            for date_str, file_path, issues in [(d, f, i) for d, f, i in results if i]:
                console.print(f"[bold cyan]{date_str}[/bold cyan]  [yellow]{' · '.join(issues)}[/yellow]")
                _fix_file_interactively(manager, date_str, file_path, issues)
                console.print()

    return app
