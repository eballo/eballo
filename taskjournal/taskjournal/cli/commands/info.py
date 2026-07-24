from datetime import timedelta
from importlib.metadata import version, PackageNotFoundError
from os.path import exists, isdir, join as path_join

from taskjournal.cli.animations import run_marquee

from rich.panel import Panel
from rich.table import Table
from typer import Typer, Context, Option

from taskjournal.cli.context import get_container, get_manager, get_today, parse_date
from taskjournal.config import (
    AI_PROVIDER,
    BASE_DIR,
    BACKUP_DIR,
    DAILY_ALARMS_ENABLED,
    EDITOR_APP,
    HOLIDAYS_FILE,
    MANAGER_NAME,
    TEMPLATE_FORMAT,
)
from taskjournal.services.calendar.fireman import FiremanService
from taskjournal.services.calendar.holidays import HolidayService
from taskjournal.models.task import Status
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
        manager = get_manager(ctx)

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
        week_num = today.isocalendar()[1]
        table.add_row("Week", str(week_num))

        daily_file, week_folder = TimeService.resolve_daily_notes_file(today)
        notes_ok = exists(daily_file)
        table.add_row(
            "Daily notes",
            _ok(daily_file) if notes_ok else f"[yellow]{daily_file} (not created yet)[/yellow]",
        )

        parsed = container.daily_parser().parse(daily_file) if notes_ok else None

        if parsed and parsed.work_from:
            location: str | None = parsed.work_from
        else:
            location = manager.get_wifi_location()
        table.add_row("Location", location or "[dim]unknown[/dim]")

        if parsed:
            finalized = bool(parsed.end_time and parsed.end_time.strip())
            table.add_row(
                "Finalized",
                _ok(f"yes  (end: {parsed.end_time})") if finalized else "[yellow]no[/yellow]",
            )
            tasks = parsed.planned_tasks + parsed.code_review_tasks
            done = sum(1 for t in tasks if t.status == Status.DONE)
            blocked = sum(1 for t in tasks if t.status == Status.BLOCKED)
            in_progress = sum(1 for t in tasks if t.status in (Status.IN_PROGRESS, Status.CODE_REVIEW))
            total = len(tasks)
            parts = [f"{done}/{total} done"]
            if in_progress:
                parts.append(f"{in_progress} in progress")
            if blocked:
                parts.append(f"[red]{blocked} blocked[/red]")
            table.add_row("Tasks", "  ·  ".join(parts) if total else "[dim]none[/dim]")

        streak = manager.get_streak_stats(today)
        table.add_row(
            "Streak",
            f"{streak['current']} day(s)  [dim]best: {streak['longest']}[/dim]",
        )
        table.add_row("", "")

        # ── Week ─────────────────────────────────────────────────────────────
        _section(table, "Week")
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)
        table.add_row("Dates", f"{monday.strftime('%d %b')} – {friday.strftime('%d %b %Y')}")

        accumulated_s = TimeService.get_accumulated_week_seconds(week_folder, today)
        expected_s = TimeService.get_expected_week_seconds_before(week_folder, today)
        extra_s = accumulated_s - expected_s
        acc_h, acc_m = TimeService.seconds_to_hours_minutes(accumulated_s)
        exp_h, exp_m = TimeService.seconds_to_hours_minutes(expected_s)
        extra_sign = "+" if extra_s >= 0 else "-"
        ext_h, ext_m = TimeService.seconds_to_hours_minutes(abs(extra_s))
        table.add_row(
            "Hours",
            f"{acc_h}h {acc_m:02d}m accumulated  ·  {exp_h}h {exp_m:02d}m expected  ·  "
            f"[{'green' if extra_s >= 0 else 'yellow'}]{extra_sign}{ext_h}h {ext_m:02d}m[/{'green' if extra_s >= 0 else 'yellow'}]",
        )
        table.add_row("", "")

        # ── Calendar ─────────────────────────────────────────────────────────
        _section(table, "Calendar")
        holidays_path = path_join(str(BASE_DIR), f"{today.year}/{HOLIDAYS_FILE}")
        try:
            holiday_svc = HolidayService(filepath=holidays_path)
            today_key = today.replace(hour=0, minute=0, second=0, microsecond=0)
            today_holiday = holiday_svc.is_holiday(today_key)
            if today_holiday:
                table.add_row("Today", f"[cyan]holiday: {today_holiday.get('description', '')}[/cyan]")
            days_until, next_hol_date, next_hol_desc = holiday_svc.get_days_until_next_holiday()
            if next_hol_date:
                table.add_row(
                    "Next holiday",
                    f"{next_hol_desc}  [dim]({next_hol_date.strftime('%d %b')} · in {days_until}d)[/dim]",
                )
            else:
                table.add_row("Next holiday", "[dim]none scheduled[/dim]")
        except Exception:
            table.add_row("Holidays", "[dim]not configured[/dim]")

        try:
            fireman_svc = FiremanService(create_datetime=today)
            fireman_svc.load_and_parse()
            if fireman_svc.is_fireman_week():
                table.add_row("Firefighter", "[yellow]this is a firefighter week[/yellow]")
            days_ff, next_ff_date = fireman_svc.get_next_week(today.date())
            if next_ff_date:
                table.add_row(
                    "Next firefighter",
                    f"[dim]{next_ff_date.strftime('%d %b %Y')} · in {days_ff}d[/dim]",
                )
        except Exception:
            pass
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

        # ── Alarms ───────────────────────────────────────────────────────────
        _section(table, "Alarms")
        table.add_row(
            "Daily alarms",
            _ok("enabled") if DAILY_ALARMS_ENABLED else "[yellow]disabled[/yellow]",
        )
        if DAILY_ALARMS_ENABLED:
            today_str = today.strftime("%Y-%m-%d")
            today_alarms = [a for a in manager.list_alarms() if str(a["date"]) == today_str]
            if today_alarms:
                for a in today_alarms:
                    time_str = str(a["scheduled"]) if a["scheduled"] else "?"
                    msg = str(a["message"]) if a.get("message") else "—"
                    is_alive = bool(a.get("is_alive", False))
                    is_past = bool(a["is_past"])
                    if is_alive:
                        status = "[green]active[/green]"
                    elif is_past:
                        status = "[dim]expired[/dim]"
                    else:
                        status = "[yellow]stopped[/yellow]"
                    table.add_row("", f"{time_str}  {msg}  {status}")
            else:
                table.add_row("", "[dim]no alarms for today[/dim]")
        table.add_row("", "")

        # ── Tools ────────────────────────────────────────────────────────────
        _section(table, "Tools")
        table.add_row("Editor", EDITOR_APP or "[dim]not set[/dim]")
        table.add_row("Manager", MANAGER_NAME or "[dim]not set[/dim]")

        console.print(table)

        day_label = today.strftime("%A, %d %B %Y")
        run_marquee(f"📅 Week {week_num} · {day_label} · wk v{pkg_version}", style="dim", duration=2.5)

    return app
