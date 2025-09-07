from typer import Typer, Context

from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="Monthly reporting commands.",
        no_args_is_help=True,
    )

    @app.command(
        "report",
        help="Create a monthly report .\n\n Examples:\n wk month report\n",
    )
    def month_report(
        ctx: Context,
    ):
        debug = ctx.obj.get("debug", False)
        custom_date = ctx.obj.get("today")
        m = ctx.obj.get("manager")
        logger.debug(f"debug={debug}")
        m.create_month_review(custom_date)

    return app
