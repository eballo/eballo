import asyncio
from datetime import datetime
from typing import Optional

from click.exceptions import Exit
from typer import Typer, Context, Option

from taskjournal.config import GIT_HUB_ORGANIZATION_NAME
from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="Create a Retrospective",
        no_args_is_help=True,
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
        debug = ctx.obj.get("debug", False)
        m = ctx.obj.get("manager")
        logger.debug(f" debug={debug},")

        service = m.jira

        if all:
            logger.info("📝 All Tasks:")
            tasks = asyncio.run(service.get_current_sprint_tasks())
        elif mine:
            logger.info("📝 Current Sprint Tasks ALL assigned to me:")
            tasks = asyncio.run(service.get_current_sprint_tasks_all_assigned_to_me())
        elif code:
            logger.info("📝 Current Sprint Tasks in Code Review:")
            tasks = asyncio.run(service.get_current_sprint_tasks_in_code_review())
        elif midreview:
            logger.info("📝 Current Tasks assigned to me in the last 6 months:")
            tasks = asyncio.run(
                service.get_current_tasks_assigned_to_me_last_6_months()
            )
        elif month:
            logger.info("📝 Current Tasks assigned to me in the last month:")
            tasks = asyncio.run(service.get_current_tasks_assigned_to_me_last_month())
        else:
            logger.info("📝 Current Sprint Tasks assigned to me (not finished):")
            tasks = asyncio.run(
                service.get_current_sprint_tasks_not_done_assigned_to_me()
            )

        for task in tasks:
            logger.info(task)

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
        date: Optional[str] = Option(
            None, help="Override the date (format: 'YYYY-MM-DD')"
        ),
        contributed: bool = Option(True, help="only show contributed commits"),
        organization: str = Option(
            help="GitHub organization name", default=GIT_HUB_ORGANIZATION_NAME
        ),
    ) -> None:
        debug = ctx.obj.get("debug", False)
        m = ctx.obj.get("manager")
        logger.debug(f"debug={debug}")

        if (date or contributed is not None) and not stats:
            logger.info(
                "❌ The '--date' and '--contributed' options can only be used together with '--stats'."
            )
            raise Exit(code=1)

        service = m.github
        service.org_name = organization

        if stats:
            if date:
                try:
                    custom_date = datetime.strptime(date, "%Y-%m-%d")
                    commit_stats = asyncio.run(
                        service.get_org_commit_stats(
                            since_date=custom_date,
                            only_contributed=contributed,
                        )
                    )

                except ValueError:
                    logger.error("❌ Invalid date format. Use 'YYYY-MM-DD'.")
                    raise Exit(code=1)

            else:
                commit_stats = asyncio.run(
                    service.get_org_commit_stats(only_contributed=contributed)
                )
            service.print_commit_stats(commit_stats)

    return app
