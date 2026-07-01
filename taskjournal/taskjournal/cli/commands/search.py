from os.path import basename, dirname

from rich.panel import Panel
from rich.text import Text
from typer import Context, Option, Typer

from taskjournal.cli.context import get_manager, get_today, parse_date
from taskjournal.services.logger import console, logger


def build_app() -> Typer:
    app = Typer(
        help="Search across all note and report files.",
        no_args_is_help=True,
        invoke_without_command=True,
    )

    @app.callback(invoke_without_command=True)
    def search_run(
        ctx: Context,
        query: str = Option(..., "--query", "-q", help="Keyword or phrase to search for."),
        from_date: str | None = Option(None, "--from", help="Start date filter: 'YYYY-MM-DD'."),
        to_date: str | None = Option(None, "--to", help="End date filter: 'YYYY-MM-DD'."),
        note_type: str | None = Option(
            None,
            "--type",
            help="File type to search: 'daily', 'week', or omit for all.",
        ),
    ) -> None:
        manager = get_manager(ctx)
        today = get_today(ctx)

        fd = parse_date(from_date) if from_date else None
        td = parse_date(to_date) if to_date else today

        console.print(Panel(f"[bold]wk search[/bold] — [italic]{query}[/italic]", expand=False))

        results = manager.search_notes(query, fd, td, note_type)

        if not results:
            console.print("[dim]No matches found.[/dim]")
            return

        current_file = ""
        match_count = 0

        for file_path, lineno, line_text in results:
            if file_path != current_file:
                rel = _short_path(file_path)
                console.print(f"\n[bold cyan]{rel}[/bold cyan]")
                current_file = file_path

            highlighted = _highlight(line_text, query)
            console.print(f"  [dim]{lineno:>4}[/dim]  {highlighted}")
            match_count += 1

        console.print(f"\n[dim]{match_count} match{'es' if match_count != 1 else ''} in {len({r[0] for r in results})} file(s).[/dim]")

    return app


def _short_path(file_path: str) -> str:
    """Return week-folder/filename for display."""
    return basename(dirname(file_path)) + "/" + basename(file_path)


def _highlight(line: str, query: str) -> Text:
    """Return a Rich Text with the query highlighted."""
    text = Text()
    lower_line = line.lower()
    lower_query = query.lower()
    pos = 0
    while True:
        idx = lower_line.find(lower_query, pos)
        if idx == -1:
            text.append(line[pos:])
            break
        text.append(line[pos:idx])
        text.append(line[idx : idx + len(query)], style="bold yellow")
        pos = idx + len(query)
    return text
