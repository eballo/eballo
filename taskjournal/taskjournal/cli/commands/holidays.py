import os.path
from datetime import datetime
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

    def get_common_logic(ctx: Context, year: str | None) -> tuple[Any, str]:
        if not year:
            logger.warning("Getting default year")
            year = datetime.now().year
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
        year: str = Option(
            None, "--year", "-y", help="Year for which to get holidays."
        ),
    ):
        debug, holidays_path = get_common_logic(ctx, year)
        service = HolidayService(debug=debug, filepath=holidays_path)
        service.summary_all()
        return app

    @app.command(
        "upcoming",
        help="get all the upcoming.\n\nExamples:\n  wk holidays upcoming\n",
    )
    def holidays_upcoming(
        ctx: Context,
        year: str = Option(
            None, "--year", "-y", help="Year for which to get holidays."
        ),
    ):
        debug, holidays_path = get_common_logic(ctx, year)
        service = HolidayService(debug=debug, filepath=holidays_path)
        service.summary_upcoming()
        return app

    @app.command("populate", help="Generate Markdown files for holidays.")
    def holidays_populate(
        ctx: Context,
        year: str = Option(
            None, "--year", "-y", help="Year for which to populate files."
        ),
    ):
        debug, holidays_path = get_common_logic(ctx, year)
        service = HolidayService(debug=debug, filepath=holidays_path)
        service.populate_files()

    return app
