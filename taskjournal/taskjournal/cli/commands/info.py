from os.path import exists, isdir

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typer import Typer, Context, Option

from taskjournal.cli.context import get_container, get_today, parse_date
from taskjournal.config import BASE_DIR, TEMPLATE_FORMAT
from taskjournal.services.base import BaseService, ServiceStatus
from taskjournal.services.setup import ENV_PATH

console = Console()

_ICON = {
    ServiceStatus.OK: "[green]✓[/green]",
    ServiceStatus.WARNING: "[yellow]⚠[/yellow]",
    ServiceStatus.UNCONFIGURED: "[yellow]⚠[/yellow]",
    ServiceStatus.ERROR: "[red]✗[/red]",
}
_STYLE = {
    ServiceStatus.OK: "green",
    ServiceStatus.WARNING: "yellow",
    ServiceStatus.UNCONFIGURED: "yellow",
    ServiceStatus.ERROR: "red",
}


def build_app() -> Typer:
    app = Typer(
        help="General information commands.",
        no_args_is_help=True,
    )

    @app.command(
        "show",
        help=(
            "Show current date, week and integration status.\n\n"
            "Examples:\n"
            "  wk info show\n"
            "  wk info show --date 2025-08-31\n"
        ),
    )
    def show(
        ctx: Context,
        date: str | None = Option(
            None,
            "--date",
            help="Show info for a specific date: 'YYYY-MM-DD'.",
        ),
    ) -> None:
        today = parse_date(date) if date else get_today(ctx)
        container = get_container(ctx)

        console.print(Panel("[bold]wk info[/bold]", expand=False))

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("label", style="dim", width=18)
        table.add_column("value")

        table.add_row("Today", today.strftime("%A, %Y-%m-%d"))
        table.add_row("Week", str(today.isocalendar()[1]))
        table.add_row("", "")

        env_ok = ENV_PATH.exists()
        table.add_row(
            "Config file",
            f"[green]{ENV_PATH}[/green]" if env_ok else "[red]Not found — run wk setup[/red]",
        )

        base_ok = exists(str(BASE_DIR)) and isdir(str(BASE_DIR))
        table.add_row(
            "BASE_DIR",
            f"[green]{BASE_DIR}[/green]" if base_ok else f"[red]{BASE_DIR} (missing)[/red]",
        )
        table.add_row("Template format", TEMPLATE_FORMAT)
        table.add_row("", "")

        integrations: list[tuple[str, BaseService]] = [
            ("Jira", container.jira()),
            ("GitHub", container.github()),
            ("AI", container.ai_service()),
            ("WiFi", container.wifi_service()),
        ]

        for name, svc in integrations:
            result = svc.health_check()
            style = _STYLE[result.status]
            icon = _ICON[result.status]
            table.add_row(name, f"[{style}]{icon} {result.message}[/{style}]")

        console.print(table)

    return app
