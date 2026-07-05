from typer import Context, Typer

from taskjournal.cli.context import get_manager, get_today
from taskjournal.services.logger import console


def build_app() -> Typer:
    app = Typer(
        help="Generate standup text from yesterday's done tasks and today's planned ones.",
        no_args_is_help=False,
        invoke_without_command=True,
    )

    @app.callback(invoke_without_command=True)
    def standup(ctx: Context) -> None:
        """Show standup summary: yesterday done, done today, today planned, blockers."""
        m = get_manager(ctx)
        today = get_today(ctx)
        data = m.get_standup(today)

        done = data["done"]
        today_done = data["today_done"]
        today_tasks = data["today"]
        blockers = data["blockers"]

        console.print()
        console.print("[bold]Yesterday[/bold]")
        if done:
            for t in done:
                console.print(f"  [green]✓[/green] {t}")
        else:
            console.print("  [dim]nothing recorded[/dim]")

        if today_done:
            console.print()
            console.print("[bold]Done today[/bold]")
            for t in today_done:
                console.print(f"  [green]✓[/green] {t}")

        console.print()
        console.print("[bold]Today[/bold]")
        if today_tasks:
            for t in today_tasks:
                console.print(f"  [cyan]○[/cyan] {t}")
        else:
            console.print("  [dim]nothing planned yet[/dim]")

        console.print()
        console.print("[bold]Blockers[/bold]")
        if blockers:
            for t in blockers:
                console.print(f"  [red]✗[/red] {t}")
        else:
            console.print("  [dim]none[/dim]")

        console.print()

    return app
