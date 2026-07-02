from asyncio import run

from rich.table import Table
from typer import Typer, Context

from taskjournal.cli.context import get_manager, get_today
from taskjournal.services.logger import console, logger


def build_app() -> Typer:
    app = Typer(
        help="Pull request commands.",
        no_args_is_help=True,
    )

    @app.command("list", help="List open PRs waiting for your review.")
    def list_prs(ctx: Context) -> None:
        prs = run(get_manager(ctx).list_prs())
        if not prs:
            console.print("[dim]No PRs pending your review.[/dim]")
            return

        table = Table(show_header=True, header_style="bold")
        table.add_column("Repo", style="cyan", no_wrap=True)
        table.add_column("#", style="dim", width=6)
        table.add_column("Title")
        table.add_column("Author", style="dim")

        for pr in prs:
            table.add_row(pr.repo, str(pr.number), f"[link={pr.url}]{pr.title}[/link]", pr.author)

        console.print(table)

    @app.command("sync", help="Add PRs pending review as tasks in today's daily notes.")
    def sync_prs(ctx: Context) -> None:
        today = get_today(ctx)
        try:
            added = run(get_manager(ctx).sync_prs(today))
            if added == 0:
                console.print("[green]✓[/green] All PRs already in daily notes.")
            else:
                console.print(f"[green]✓[/green] Added {added} PR(s) to daily notes.")
        except FileNotFoundError as e:
            logger.error(str(e))

    return app
