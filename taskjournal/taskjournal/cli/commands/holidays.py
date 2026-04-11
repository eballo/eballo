import os.path
from typing import Any

from typer import Typer, Context, Option

from taskjournal.config import BASE_DIR, HOLIDAYS_FILE
from taskjournal.services.holidays import HolidayService
from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="Holidays command.",
        no_args_is_help=True,
    )

    def get_common_logic(ctx: Context, year: str | None = None) -> tuple[Any, str]:
        if not year:
            logger.debug("Getting default year")
            custom_date = ctx.obj.get("today")
            year = custom_date.year
        debug = ctx.obj.get("debug", False)
        holidays_path = os.path.join(BASE_DIR, f"{year}/{HOLIDAYS_FILE}")
        logger.debug(f"debug={debug}, path={holidays_path}")
        return debug, holidays_path

    @app.command(
        "all",
        help="get all holidays.\n\nExamples:\n  wk holidays all\n",
    )
    def holidays_all(
        ctx: Context,
        year: str | None = Option(
            None, "--year", "-y", help="Year for which to get holidays."
        ),
        sort_by: str = Option(
            "date",
            "--sort-by",
            "-s",
            show_default=False,
            help="Sort holidays by 'category' or 'date'",
        ),
    ) -> None:
        debug, holidays_path = get_common_logic(ctx, year)
        service = HolidayService(debug=debug, filepath=holidays_path)
        service.summary_all(sort_by=sort_by)

    @app.command(
        "upcoming",
        help="get all the upcoming.\n\nExamples:\n  wk holidays upcoming\n",
    )
    def holidays_upcoming(
        ctx: Context,
        year: str | None = Option(
            None, "--year", "-y", help="Year for which to get holidays."
        ),
        sort_by: str = Option(
            "date",
            "--sort-by",
            "-s",
            show_default=False,
            help="Sort holidays by 'category' or 'date'",
        ),
    ) -> None:
        debug, holidays_path = get_common_logic(ctx, year)
        service = HolidayService(debug=debug, filepath=holidays_path)
        service.summary_upcoming(sort_by=sort_by)

    @app.command(
        "past",
        help="get all the past holidays.\n\nExamples:\n  wk holidays past\n",
    )
    def holidays_past(
        ctx: Context,
        year: str | None = Option(
            None, "--year", "-y", help="Year for which to get holidays."
        ),
        sort_by: str = Option(
            "date",
            "--sort-by",
            "-s",
            show_default=False,
            help="Sort holidays by 'category' or 'date'",
        ),
    ) -> None:
        debug, holidays_path = get_common_logic(ctx, year)
        service = HolidayService(debug=debug, filepath=holidays_path)
        service.summary_past(sort_by=sort_by)

    @app.command(
        "summary",
        help="Get a summary of holidays (done, remaining, next).\n\nExamples:\n  wk holidays summary\n",
    )
    def holidays_summary(
        ctx: Context,
        year: str | None = Option(
            None, "--year", "-y", help="Year for which to get summary."
        ),
    ) -> None:
        debug, holidays_path = get_common_logic(ctx, year)
        service = HolidayService(debug=debug, filepath=holidays_path)
        service.summary()

    @app.command("populate", help="Generate Markdown files for holidays.")
    def holidays_populate(
        ctx: Context,
        year: str | None = Option(
            None, "--year", "-y", help="Year for which to populate files."
        ),
    ) -> None:
        debug, holidays_path = get_common_logic(ctx, year)
        service = HolidayService(debug=debug, filepath=holidays_path)
        service.populate_files()

    @app.command(
        "days_until_next_holiday", help="Get the number of days until the next holiday."
    )
    def holidays_days_until_next_holiday(ctx: Context):
        debug, holidays_path = get_common_logic(ctx)
        service = HolidayService(debug=debug, filepath=holidays_path)
        days_until_next_holiday, next_holiday_date, next_holiday_description = (
            service.get_days_until_next_holiday()
        )
        logger.info(
            f"There are {days_until_next_holiday} day(s) until the next holiday. "
            f"Next holiday: {next_holiday_description} on {next_holiday_date}"
        )

    return app
