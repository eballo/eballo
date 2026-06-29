import os.path
from typing import Any

from typer import Argument, Typer, Context, Option

from taskjournal.cli.context import get_today, get_debug
from taskjournal.config import BASE_DIR, HOLIDAYS_FILE
from taskjournal.services.holidays import HolidayService
from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="Holidays command.",
        no_args_is_help=True,
    )

    def get_service(ctx: Context, year: str | None = None) -> HolidayService:
        if not year:
            logger.debug("Getting default year")
            year = str(get_today(ctx).year)
        debug = get_debug(ctx)
        holidays_path = os.path.join(BASE_DIR, f"{year}/{HOLIDAYS_FILE}")
        logger.debug(f"debug={debug}, path={holidays_path}")
        return HolidayService(debug=debug, filepath=holidays_path)

    common_year_option: Any = Option(
        None, "--year", "-y", help="Year for which to get holidays."
    )
    common_sort_option: Any = Option(
        "date",
        "--sort-by",
        "-s",
        show_default=False,
        help="Sort holidays by 'category' or 'date'",
    )

    @app.command(
        "all",
        help="get all holidays.\n\nExamples:\n  wk holidays all\n",
    )
    def holidays_all(
        ctx: Context,
        year: str | None = common_year_option,
        sort_by: str = common_sort_option,
    ) -> None:
        get_service(ctx, year).summary_all(sort_by=sort_by)

    @app.command(
        "upcoming",
        help="get all the upcoming.\n\nExamples:\n  wk holidays upcoming\n",
    )
    def holidays_upcoming(
        ctx: Context,
        year: str | None = common_year_option,
        sort_by: str = common_sort_option,
    ) -> None:
        get_service(ctx, year).summary_upcoming(sort_by=sort_by)

    @app.command(
        "past",
        help="get all the past holidays.\n\nExamples:\n  wk holidays past\n",
    )
    def holidays_past(
        ctx: Context,
        year: str | None = common_year_option,
        sort_by: str = common_sort_option,
    ) -> None:
        get_service(ctx, year).summary_past(sort_by=sort_by)

    @app.command(
        "summary",
        help="Get a summary of holidays (done, remaining, next).\n\nExamples:\n  wk holidays summary\n",
    )
    def holidays_summary(
        ctx: Context,
        year: str | None = common_year_option,
    ) -> None:
        get_service(ctx, year).summary()

    @app.command("add", help="Add a holiday to the holidays file.")
    def holidays_add(
        ctx: Context,
        date: str = Argument(..., help="Date in YYYY-MM-DD format."),
        description: str = Argument(..., help="Holiday description."),
        category: str = Option("Personal days", "--category", "-c", help="Category section to add under."),
        year: str | None = common_year_option,
    ) -> None:
        svc = get_service(ctx, year)
        resolved_year = year or str(get_today(ctx).year)
        holidays_path = os.path.join(BASE_DIR, f"{resolved_year}/{HOLIDAYS_FILE}")
        svc.add_holiday(holidays_path, date, description, category)

    @app.command("populate", help="Generate Markdown files for holidays.")
    def holidays_populate(
        ctx: Context,
        year: str | None = common_year_option,
    ) -> None:
        get_service(ctx, year).populate_files()

    @app.command(
        "days_until_next_holiday", help="Get the number of days until the next holiday."
    )
    def holidays_days_until_next_holiday(ctx: Context) -> None:
        days, next_date, description = get_service(ctx).get_days_until_next_holiday()
        logger.info(
            f"There are {days} day(s) until the next holiday. "
            f"Next holiday: {description} on {next_date}"
        )

    return app
