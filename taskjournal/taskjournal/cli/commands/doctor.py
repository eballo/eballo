from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typer import Context, Typer

from taskjournal.cli.context import get_container
from taskjournal.services.base import HealthCheckResult, ServiceStatus
from taskjournal.services.setup import ENV_PATH

console = Console()

_STATUS_ICON = {
    ServiceStatus.OK: "[green]✓[/green]",
    ServiceStatus.WARNING: "[yellow]⚠[/yellow]",
    ServiceStatus.UNCONFIGURED: "[yellow]⚠[/yellow]",
    ServiceStatus.ERROR: "[red]✗[/red]",
}

_STATUS_STYLE = {
    ServiceStatus.OK: "green",
    ServiceStatus.WARNING: "yellow",
    ServiceStatus.UNCONFIGURED: "yellow",
    ServiceStatus.ERROR: "red",
}


def build_app() -> Typer:
    app = Typer(
        help="Run a health check on all services and configuration.",
        no_args_is_help=False,
        invoke_without_command=True,
    )

    @app.callback(invoke_without_command=True)
    def doctor_run(ctx: Context) -> None:
        """Check configuration and external integrations."""
        container = get_container(ctx)

        checks: list[tuple[str, HealthCheckResult]] = []

        # Config file
        checks.append(_check_config_file())

        # Services with meaningful health checks
        checks.append(("Backup / Paths", container.backup_service().health_check()))
        checks.append(("WiFi detection", container.wifi_service().health_check()))
        checks.append(("Jira", container.jira().health_check()))
        checks.append(("GitHub", container.github().health_check()))
        checks.append(("AI", container.ai_service().health_check()))

        _print_report(checks)

    return app


def _check_config_file() -> tuple[str, HealthCheckResult]:
    if not ENV_PATH.exists():
        return (
            "Config file",
            HealthCheckResult(
                ServiceStatus.ERROR,
                f"Not found: {ENV_PATH}",
                ["Run 'wk setup' to create it"],
            ),
        )
    return (
        "Config file",
        HealthCheckResult(ServiceStatus.OK, str(ENV_PATH)),
    )


def _print_report(checks: list[tuple[str, HealthCheckResult]]) -> None:
    console.print(
        Panel("[bold]wk doctor[/bold] — Health check", expand=False)
    )

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("icon", no_wrap=True, width=3)
    table.add_column("name", style="bold", width=20)
    table.add_column("message")

    counts = {ServiceStatus.OK: 0, ServiceStatus.WARNING: 0,
              ServiceStatus.ERROR: 0, ServiceStatus.UNCONFIGURED: 0}

    for name, result in checks:
        icon = _STATUS_ICON[result.status]
        style = _STATUS_STYLE[result.status]
        table.add_row(icon, name, f"[{style}]{result.message}[/{style}]")
        for detail in result.details:
            table.add_row("", "", f"  [dim]{detail}[/dim]")
        counts[result.status] += 1

    console.print(table)
    console.print()

    ok = counts[ServiceStatus.OK]
    warnings = counts[ServiceStatus.WARNING] + counts[ServiceStatus.UNCONFIGURED]
    errors = counts[ServiceStatus.ERROR]

    parts = [f"[green]{ok} OK[/green]"]
    if warnings:
        parts.append(f"[yellow]{warnings} warning{'s' if warnings > 1 else ''}[/yellow]")
    if errors:
        parts.append(f"[red]{errors} error{'s' if errors > 1 else ''}[/red]")

    console.print("Summary: " + "  ·  ".join(parts))

    if errors:
        console.print("\n[dim]Run [bold]wk setup[/bold] to fix missing configuration.[/dim]")
