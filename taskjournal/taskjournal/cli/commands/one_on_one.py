from typer import Typer, Context

from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="1on1 reporting commands.",
        no_args_is_help=True,
    )

    @app.command(
        "report",
        help="Create a 1on1 report .\n\n Examples:\n wk 1on1 report\n",
    )
    def one_on_one_report(
        ctx: Context,
    ) -> None:
        debug = ctx.obj.get("debug", False)
        custom_date = ctx.obj.get("today")
        m = ctx.obj.get("manager")
        logger.debug(f"debug={debug}")
        m.create_one_on_one(custom_date)

    return app
