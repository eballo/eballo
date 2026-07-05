from sys import exit as sys_exit

from rich.table import Table
from typer import Argument, Context, Option, Typer

from taskjournal.cli.context import get_manager, get_today, parse_date
from taskjournal.services.logger import console, logger


def build_app() -> Typer:
    app = Typer(
        help="Log and review professional feedback (received and given).",
        no_args_is_help=True,
        pretty_exceptions_enable=False,
    )

    @app.command(
        "received",
        help=(
            "Log feedback you received.\n\n"
            "Examples:\n"
            "  wk feedback received 'Great PR review' --from 'Maria' --context 'PR #142'\n"
        ),
    )
    def feedback_received(
        ctx: Context,
        text: str = Argument(..., help="Feedback text."),
        from_person: str = Option(..., "--from", "-f", help="Who gave the feedback."),
        context: str = Option("", "--context", "-c", help="Optional context (PR, 1:1, etc.)."),
        date: str = Option(None, "--date", help="Date: 'YYYY-MM-DD' (default: today)."),
    ) -> None:
        target_date = parse_date(date) if date else get_today(ctx)
        m = get_manager(ctx)
        if m._feedback is None:
            logger.error("Feedback service not configured")
            sys_exit(1)
        m.add_feedback_received(text, from_person, context, target_date)
        console.print(f"[green]✓[/green] Feedback received from {from_person} recorded")

    @app.command(
        "given",
        help=(
            "Log feedback you gave.\n\n"
            "Examples:\n"
            "  wk feedback given 'Great ownership of incident' --to 'Alex' --context '1:1'\n"
        ),
    )
    def feedback_given(
        ctx: Context,
        text: str = Argument(..., help="Feedback text."),
        to_person: str = Option(..., "--to", "-t", help="Who received the feedback."),
        context: str = Option("", "--context", "-c", help="Optional context (PR, 1:1, etc.)."),
        date: str = Option(None, "--date", help="Date: 'YYYY-MM-DD' (default: today)."),
    ) -> None:
        target_date = parse_date(date) if date else get_today(ctx)
        m = get_manager(ctx)
        if m._feedback is None:
            logger.error("Feedback service not configured")
            sys_exit(1)
        m.add_feedback_given(text, to_person, context, target_date)
        console.print(f"[green]✓[/green] Feedback given to {to_person} recorded")

    @app.command(
        "list",
        help=(
            "List feedback entries.\n\n"
            "Examples:\n"
            "  wk feedback list\n"
            "  wk feedback list --quarter 2\n"
            "  wk feedback list --from 'Maria'\n"
            "  wk feedback list --type received\n"
        ),
    )
    def feedback_list(
        ctx: Context,
        year: int = Option(0, "--year", help="Year (default: current year)."),
        quarter: int = Option(0, "--quarter", "-q", help="Filter by quarter (1–4)."),
        person: str = Option("", "--from", "--to", help="Filter by person name."),
        feedback_type: str = Option("", "--type", help="Filter by type: 'received' or 'given'."),
    ) -> None:
        today = get_today(ctx)
        target_year = year if year else today.year
        m = get_manager(ctx)
        if m._feedback is None:
            logger.error("Feedback service not configured")
            sys_exit(1)

        entries = m.list_feedback(
            year=target_year,
            quarter=quarter if quarter else None,
            person=person if person else None,
            feedback_type=feedback_type if feedback_type else None,
        )

        if not entries:
            console.print("[dim]No feedback entries found.[/dim]")
            return

        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("Date", width=12)
        table.add_column("Type", width=10)
        table.add_column("Person", width=15)
        table.add_column("Context", width=15)
        table.add_column("Feedback")

        for entry in entries:
            entry_type = str(entry.get("type", ""))
            if entry_type == "received":
                person_col = str(entry.get("from_person", ""))
                type_display = "[cyan]received[/cyan]"
            else:
                person_col = str(entry.get("to_person", ""))
                type_display = "[green]given[/green]"

            table.add_row(
                str(entry.get("date", "")),
                type_display,
                person_col,
                str(entry.get("context", "")),
                str(entry.get("text", "")),
            )

        console.print(table)

    return app
