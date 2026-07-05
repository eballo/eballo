from asyncio import run
from datetime import datetime

from sys import exit as sys_exit
from rich.table import Table
from typer import Typer, Context, Option

from taskjournal.cli.context import get_manager, get_debug, get_today, parse_date
from taskjournal.config import GIT_HUB_ORGANIZATION_NAME
from taskjournal.constants import (
    JIRA_MODE_ALL,
    JIRA_MODE_CODE,
    JIRA_MODE_DEFAULT,
    JIRA_MODE_MIDREVIEW,
    JIRA_MODE_MINE,
    JIRA_MODE_MONTH,
)
from taskjournal.services.integrations.github import GithubService
from taskjournal.services.logger import console, logger


def build_app() -> Typer:
    app = Typer(
        help="Create a Retrospective",
        no_args_is_help=True,
        pretty_exceptions_enable=False,
    )

    @app.command(
        "jira",
        help=(
            "To easily run Jira Service"
            "Examples:\n"
            "  wk services jira all\n"
            "  wk services jira mine\n"
            "  wk services jira code\n"
            "  wk services jira midreview\n"
            "  wk services jira month\n"
        ),
    )
    def jira(
        ctx: Context,
        all: bool = Option(False, "--all", help="Get ALL tasks of the sprint"),
        mine: bool = Option(False, "--mine", help="Get ALL tasks assigned to me"),
        code: bool = Option(
            False, "--code", help="Get ALL tasks in status 'Code Review'"
        ),
        midreview: bool = Option(
            False,
            "--midreview",
            help="Get ALL tasks performed by me in the last 6 months",
        ),
        month: bool = Option(
            False, "--month", help="Get ALL tasks performed by me in the last month"
        ),
    ) -> None:
        logger.debug(f"debug={get_debug(ctx)}")
        m = get_manager(ctx)

        if all:
            console.print("📝 All Tasks:")
            mode = JIRA_MODE_ALL
        elif mine:
            console.print("📝 Current Sprint Tasks ALL assigned to me:")
            mode = JIRA_MODE_MINE
        elif code:
            console.print("📝 Current Sprint Tasks in Code Review:")
            mode = JIRA_MODE_CODE
        elif midreview:
            console.print("📝 Current Tasks assigned to me in the last 6 months:")
            mode = JIRA_MODE_MIDREVIEW
        elif month:
            console.print("📝 Current Tasks assigned to me in the last month:")
            mode = JIRA_MODE_MONTH
        else:
            console.print("📝 Current Sprint Tasks assigned to me (not finished):")
            mode = JIRA_MODE_DEFAULT

        tasks = run(m.get_jira_tasks(mode))
        for task in tasks:
            console.print(task)

    @app.command(
        "git",
        help=(
            "To easily run Github Service"
            "Examples:\n"
            "  wk services git stats\n"
            "  wk services git date\n"
            "  wk services git contributed\n"
            "  wk services git organization\n"
        ),
    )
    def git(
        ctx: Context,
        stats: bool = Option(False, help="Get commit stats for the organization"),
        date: str | None = Option(
            None, help="Override the date (format: 'YYYY-MM-DD')"
        ),
        contributed: bool = Option(True, help="only show contributed commits"),
        organization: str = Option(
            help="GitHub organization name", default=GIT_HUB_ORGANIZATION_NAME
        ),
    ) -> None:
        logger.debug(f"debug={get_debug(ctx)}")

        if (date or contributed is not None) and not stats:
            console.print(
                "❌ The '--date' and '--contributed' options can only be used together with '--stats'."
            )
            sys_exit(1)

        if stats:
            custom_date = parse_date(date) if date else None
            commit_stats = run(
                get_manager(ctx).get_github_stats(
                    since_date=custom_date,
                    only_contributed=contributed,
                    org_name=organization,
                )
            )
            GithubService.print_commit_stats(commit_stats)

    @app.command(
        "screentime",
        help=(
            "Show macOS Screen Time usage for a given day.\n\n"
            "Requires SCREEN_TIME_ENABLED=true in .env and Full Disk Access granted to Terminal.\n\n"
            "Examples:\n"
            "  wk services screentime\n"
            "  wk services screentime --date 2026-07-01\n"
        ),
    )
    def screentime(
        ctx: Context,
        date: str = Option(None, "--date", help="Date: 'YYYY-MM-DD' (default: today)."),
    ) -> None:
        m = get_manager(ctx)
        target_date = parse_date(date) if date else get_today(ctx)
        usage = m.get_screen_time(target_date)

        if not usage:
            console.print("[dim]No Screen Time data available for this date.[/dim]")
            console.print("[dim]Make sure SCREEN_TIME_ENABLED=true and Full Disk Access is granted.[/dim]")
            return

        total_seconds = sum(s for _, s in usage)
        total_h, total_m = divmod(total_seconds // 60, 60)
        console.print(f"[bold]Screen Time for {target_date.strftime('%Y-%m-%d')}[/bold] — Total: {total_h}h {total_m}m\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("App", min_width=20)
        table.add_column("Time", justify="right", width=10)
        table.add_column("Share", width=20)

        for app_name, seconds in usage[:15]:
            h, m = divmod(seconds // 60, 60)
            share = seconds / total_seconds if total_seconds else 0
            bar_len = max(1, int(share * 18))
            bar = "█" * bar_len + "░" * (18 - bar_len)
            table.add_row(app_name, f"{h}h {m:02d}m", bar)

        console.print(table)

    @app.command(
        "claude",
        help=(
            "Quick test for the active AI service.\n\n"
            "Examples:\n"
            "  wk services claude\n"
            "  wk services claude --prompt 'Summarize: fixed a bug'\n"
        ),
    )
    def claude(
        ctx: Context,
        prompt: str = Option(
            "Say hello and tell me which model you are in one sentence.",
            "--prompt",
            help="Custom prompt to send to the AI service.",
        ),
    ) -> None:
        result = run(get_manager(ctx).run_ai_prompt(prompt))
        console.print(result)

    return app
