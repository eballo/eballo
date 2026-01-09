from typing import Any

from typer import Typer, Context, Option

from taskjournal.services.logger import logger
from taskjournal.services.working_days import WorkingDaysService


def build_app() -> Typer:
    app = Typer(
        help="Statistics command.",
        no_args_is_help=True,
    )

    def get_common_logic(ctx: Context, year: str | None) -> tuple[Any, str]:
        if not year:
            logger.warning("Getting default year")
            custom_date = ctx.obj.get("today")
            year = custom_date.year
        debug = ctx.obj.get("debug", False)
        logger.debug(f"debug={debug}, year={year}")
        return debug, year

    @app.command(
        "all",
        help="get all working days.\n\nExamples:\n  wk statistics all\n",
    )
    def working_days_summary(
        ctx: Context,
        year: str = Option(
            None, "--year", "-y", help="Year for which to get holidays."
        ),
    ):
        debug, year = get_common_logic(ctx, year)
        service = WorkingDaysService(year=year, debug=debug)
        service.summary()

    @app.command(
        "progress",
        help="get progress.\n\nExamples:\n  wk statistics progress\n",
    )
    def working_days_progress(
        ctx: Context,
        year: str = Option(
            None, "--year", "-y", help="Year for which to get holidays."
        ),
    ):
        debug, year = get_common_logic(ctx, year)
        service = WorkingDaysService(year=year, debug=debug)
        service.get_progress()

    @app.command(
        "real",
        help="get real working days (including holidays).\n\nExamples:\n  wk statistics real\n",
    )
    def working_days_real(
        ctx: Context,
        year: str = Option(
            None, "--year", "-y", help="Year for which to get holidays."
        ),
    ):
        debug, year = get_common_logic(ctx, year)
        service = WorkingDaysService(year=year, debug=debug)
        service.get_real_working_days()

    return app
