from typing import Any

from typer import Typer, Context, Option

from taskjournal.services.logger import logger
from taskjournal.services.working_days import WorkingDaysService  # kept for type hint


def build_app() -> Typer:
    app = Typer(
        help="Statistics command.",
        no_args_is_help=True,
    )

    def get_service(ctx: Context, year: str | None) -> WorkingDaysService:
        debug = ctx.obj.get("debug", False)
        if not year:
            logger.warning("Getting default year")
            custom_date = ctx.obj.get("today")
            final_year = custom_date.year
        else:
            logger.debug(f"debug={debug}, year={year}")
            final_year = year
        container = ctx.obj.get("container")
        return container.working_days_service(year=final_year, debug=debug)

    common_year_option: Any = Option(
        None, "--year", "-y", help="Year for which to get holidays."
    )

    @app.command(
        "all",
        help="get all working days.\n\nExamples:\n  wk statistics all\n",
    )
    def working_days_summary(
        ctx: Context,
        year: str | None = common_year_option,
    ) -> None:
        get_service(ctx, year).summary()

    @app.command(
        "progress",
        help="get progress.\n\nExamples:\n  wk statistics progress\n",
    )
    def working_days_progress(
        ctx: Context,
        year: str | None = common_year_option,
    ) -> None:
        get_service(ctx, year).get_progress()

    @app.command(
        "real",
        help="get real working days (including holidays).\n\nExamples:\n  wk statistics real\n",
    )
    def working_days_real(
        ctx: Context,
        year: str | None = common_year_option,
    ) -> None:
        get_service(ctx, year).get_real_working_days()

    return app
