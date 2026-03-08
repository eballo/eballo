import asyncio

from typer import Typer, Context

from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="Half-year reporting commands.",
        no_args_is_help=True,
    )

    @app.command(
        "report",
        help="Create a half-year report\n Examples:\n wk half-year report",
    )
    def half_year_report(
        ctx: Context,
    ) -> None:
        debug = ctx.obj.get("debug", False)
        custom_date = ctx.obj.get("today")
        m = ctx.obj.get("manager")
        logger.debug(f"debug={debug}")
        asyncio.run(m.create_half_year_review(custom_date))

    return app
