from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typer import Context, Typer

from taskjournal.cli.context import get_container
from taskjournal.services.setup import SetupService, ENV_PATH

console = Console()


def build_app() -> Typer:
    app = Typer(
        help="Interactive setup wizard to configure wk.",
        no_args_is_help=False,
        invoke_without_command=True,
    )

    @app.callback(invoke_without_command=True)
    def setup_run(ctx: Context) -> None:
        """Run the interactive configuration wizard."""
        service: SetupService = get_container(ctx).setup_service()
        existing = service.load_existing()

        _print_header(existing)

        if ENV_PATH.exists():
            update = typer.confirm(
                "\nA configuration file already exists. Update it?", default=True
            )
            if not update:
                console.print("[yellow]Setup cancelled. Existing config unchanged.[/yellow]")
                raise typer.Exit()

        values: dict[str, str] = dict(existing)

        # ── Paths ─────────────────────────────────────────────────────────
        console.print(Panel("[bold]Paths[/bold]", expand=False))
        if typer.confirm("Configure paths?", default=not service.is_configured("BASE_DIR", existing)):
            fmt = typer.prompt("Template format", default=existing["TEMPLATE_FORMAT"])
            while fmt not in ("md", "txt"):
                console.print("[red]Please enter 'md' or 'txt'.[/red]")
                fmt = typer.prompt("Template format", default=existing["TEMPLATE_FORMAT"])
            values["TEMPLATE_FORMAT"] = fmt
            values["BASE_DIR"] = typer.prompt(
                "Daily notes directory", default=existing["BASE_DIR"]
            )
            values["BACKUP_DIR"] = typer.prompt(
                "Backup directory", default=existing["BACKUP_DIR"]
            )

        # ── Jira ──────────────────────────────────────────────────────────
        console.print(Panel("[bold]Jira[/bold]", expand=False))
        jira_current = service.is_configured("JIRA_API_TOKEN", existing)
        if typer.confirm("Configure Jira integration?", default=jira_current):
            values["JIRA_ORGANIZATION"] = typer.prompt(
                "Jira organization slug (subdomain of atlassian.net)",
                default=existing["JIRA_ORGANIZATION"] if jira_current else "",
            )
            values["JIRA_EMAIL"] = typer.prompt(
                "Jira account email",
                default=existing["JIRA_EMAIL"] if jira_current else "",
            )
            values["JIRA_API_TOKEN"] = typer.prompt(
                "Jira API token",
                default=existing["JIRA_API_TOKEN"] if jira_current else "",
                hide_input=True,
            )
            values["JIRA_BOARD_ID"] = typer.prompt(
                "Jira board ID",
                default=existing["JIRA_BOARD_ID"] if jira_current else "",
            )
        else:
            values["JIRA_API_TOKEN"] = existing.get("JIRA_API_TOKEN", "your-jira-key")

        # ── GitHub ────────────────────────────────────────────────────────
        console.print(Panel("[bold]GitHub[/bold]", expand=False))
        gh_current = service.is_configured("GIT_HUB_TOKEN", existing)
        if typer.confirm("Configure GitHub integration?", default=gh_current):
            values["GIT_HUB_TOKEN"] = typer.prompt(
                "GitHub personal access token",
                default=existing["GIT_HUB_TOKEN"] if gh_current else "",
                hide_input=True,
            )
            values["GIT_HUB_ORGANIZATION_NAME"] = typer.prompt(
                "GitHub organization name",
                default=existing["GIT_HUB_ORGANIZATION_NAME"] if gh_current else "",
            )
        else:
            values["GIT_HUB_TOKEN"] = existing.get("GIT_HUB_TOKEN", "your-github-token")

        # ── OpenAI ────────────────────────────────────────────────────────
        console.print(Panel("[bold]OpenAI (AI summaries)[/bold]", expand=False))
        ai_current = service.is_configured("OPENAI_API_KEY", existing)
        if typer.confirm("Configure OpenAI for AI-generated summaries?", default=ai_current):
            values["OPENAI_API_KEY"] = typer.prompt(
                "OpenAI API key",
                default=existing["OPENAI_API_KEY"] if ai_current else "",
                hide_input=True,
            )
        else:
            values["OPENAI_API_KEY"] = existing.get("OPENAI_API_KEY", "your-openai-api-key")

        # ── WiFi ──────────────────────────────────────────────────────────
        console.print(Panel("[bold]WiFi location detection[/bold]", expand=False))
        wifi_current = service.is_configured("HOME_WIFI", existing)
        if typer.confirm(
            "Configure WiFi network names for automatic location detection?",
            default=wifi_current,
        ):
            values["HOME_WIFI"] = typer.prompt(
                "Home WiFi network name (SSID)",
                default=existing["HOME_WIFI"] if wifi_current else "",
            )
            values["OFFICE_WIFI"] = typer.prompt(
                "Office WiFi network name (SSID)",
                default=existing["OFFICE_WIFI"] if wifi_current else "",
            )

        # ── Editor ───────────────────────────────────────────────────────
        console.print(Panel("[bold]Editor[/bold]", expand=False))
        values["EDITOR_APP"] = typer.prompt(
            "macOS app to open notes with (used by wk daily audit --fix)",
            default=existing.get("EDITOR_APP", "Obsidian"),
        )

        # ── Data files ────────────────────────────────────────────────────
        year = datetime.now().year
        console.print(Panel(f"[bold]Data files ({year})[/bold]", expand=False))
        if typer.confirm(
            f"Create holidays.md and fireman_weeks.md for {year} (skipped if already exist)?",
            default=True,
        ):
            service.create_data_files(values["BASE_DIR"], year)

        # ── Write & summary ───────────────────────────────────────────────
        service.write_env(values)
        _print_summary(service, values)

    return app


def _print_header(existing: dict[str, str]) -> None:
    is_update = ENV_PATH.exists()
    action = "Update configuration" if is_update else "Initial setup"
    console.print(
        Panel(
            f"[bold green]wk setup[/bold green] — {action}\n\n"
            f"Config file: [cyan]{ENV_PATH}[/cyan]\n\n"
            "Press [bold]Enter[/bold] to keep the current value shown in parentheses.",
            title="Welcome",
            expand=False,
        )
    )


def _print_summary(service: SetupService, values: dict[str, str]) -> None:
    console.print()

    table = Table(title="Configuration summary", show_header=True, header_style="bold")
    table.add_column("Setting", style="cyan", no_wrap=True)
    table.add_column("Value")
    table.add_column("Status", justify="center")

    def _row(label: str, key: str, secret: bool = False) -> None:
        val = values.get(key, "")
        ok = service.is_configured(key, values)
        display = ("*" * min(len(val), 8) + "…" if secret and ok else val) if val else "—"
        status = "[green]✓[/green]" if ok else "[yellow]—[/yellow]"
        table.add_row(label, display, status)

    _row("Format", "TEMPLATE_FORMAT")
    _row("Daily notes dir", "BASE_DIR")
    _row("Backup dir", "BACKUP_DIR")
    table.add_section()
    _row("Jira organization", "JIRA_ORGANIZATION")
    _row("Jira email", "JIRA_EMAIL")
    _row("Jira API token", "JIRA_API_TOKEN", secret=True)
    _row("Jira board ID", "JIRA_BOARD_ID")
    table.add_section()
    _row("GitHub token", "GIT_HUB_TOKEN", secret=True)
    _row("GitHub organization", "GIT_HUB_ORGANIZATION_NAME")
    table.add_section()
    _row("OpenAI API key", "OPENAI_API_KEY", secret=True)
    table.add_section()
    _row("Home WiFi SSID", "HOME_WIFI")
    _row("Office WiFi SSID", "OFFICE_WIFI")
    table.add_section()
    _row("Editor app", "EDITOR_APP")

    console.print(table)
    console.print(
        f"\n[green]Config saved to[/green] [cyan]{ENV_PATH}[/cyan]\n"
        "Run [bold]wk info show[/bold] to verify the active configuration.\n"
    )
