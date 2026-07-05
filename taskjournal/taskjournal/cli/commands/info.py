from importlib.metadata import version, PackageNotFoundError
from os.path import exists, isdir

from taskjournal.cli.animations import run_marquee

from rich.panel import Panel
from rich.table import Table
from typer import Typer, Context, Option

from taskjournal.cli.context import get_container, get_today, parse_date
from taskjournal.config import (
    AI_PROVIDER,
    BASE_DIR,
    BACKUP_DIR,
    EDITOR_APP,
    MANAGER_NAME,
    TEMPLATE_FORMAT,
)
from taskjournal.services.base import BaseService, ServiceStatus
from taskjournal.services.logger import console
from taskjournal.services.setup import ENV_PATH
from taskjournal.services.time import TimeService

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


def _ok(value: str) -> str:
    return f"[green]{value}[/green]"


def _err(value: str) -> str:
    return f"[red]{value}[/red]"


def _section(table: Table, label: str) -> None:
    table.add_row(f"[dim]{label}[/dim]", "")


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

        try:
            pkg_version = version("taskjournal")
        except PackageNotFoundError:
            pkg_version = "dev"

        console.print(Panel(f"[bold]wk info[/bold]  [dim]v{pkg_version}[/dim]", expand=False))

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("label", style="dim", width=20)
        table.add_column("value")

        # ── System ───────────────────────────────────────────────────────────
        _section(table, "System")
        env_ok = ENV_PATH.exists()
        table.add_row(
            "Config file",
            _ok(str(ENV_PATH)) if env_ok else _err(f"{ENV_PATH} (run wk setup)"),
        )
        base_ok = exists(str(BASE_DIR)) and isdir(str(BASE_DIR))
        table.add_row(
            "BASE_DIR",
            _ok(str(BASE_DIR)) if base_ok else _err(f"{BASE_DIR} (missing)"),
        )
        backup_ok = exists(str(BACKUP_DIR)) and isdir(str(BACKUP_DIR))
        table.add_row(
            "BACKUP_DIR",
            _ok(str(BACKUP_DIR)) if backup_ok else f"[yellow]{BACKUP_DIR} (not found)[/yellow]",
        )
        table.add_row("Template format", TEMPLATE_FORMAT)
        table.add_row("", "")

        # ── Today ────────────────────────────────────────────────────────────
        _section(table, "Today")
        table.add_row("Date", today.strftime("%A, %Y-%m-%d"))
        table.add_row("Week", str(today.isocalendar()[1]))
        daily_file, _ = TimeService.resolve_daily_notes_file(today)
        notes_ok = exists(daily_file)
        table.add_row(
            "Daily notes",
            _ok(daily_file) if notes_ok else f"[yellow]{daily_file} (not created yet)[/yellow]",
        )
        table.add_row("", "")

        # ── Integrations ─────────────────────────────────────────────────────
        _section(table, "Integrations")
        integrations: list[tuple[str, BaseService]] = [
            ("Jira", container.jira()),
            ("GitHub", container.github()),
            (f"AI ({AI_PROVIDER})", container.ai_service()),
            ("WiFi", container.wifi_service()),
        ]
        for name, svc in integrations:
            result = svc.health_check()
            style = _STYLE[result.status]
            icon = _ICON[result.status]
            table.add_row(name, f"[{style}]{icon} {result.message}[/{style}]")
        table.add_row("", "")

        # ── Tools ────────────────────────────────────────────────────────────
        _section(table, "Tools")
        table.add_row("Editor", EDITOR_APP or "[dim]not set[/dim]")
        table.add_row("Manager", MANAGER_NAME or "[dim]not set[/dim]")

        console.print(table)

        week = today.isocalendar()[1]
        day_label = today.strftime("%A, %d %B %Y")
        run_marquee(f"📅 Week {week} · {day_label} · wk v{pkg_version}", style="dim", duration=2.5)

    return app
