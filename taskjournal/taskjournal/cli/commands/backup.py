from typer import Typer, Context

from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="Backup commands.",
        no_args_is_help=True,
    )

    @app.command(
        "run",
        help=("Create a backup all files" "Examples:\n" "  wk backup run\n"),
    )
    def backup_run(ctx: Context) -> None:
        debug = ctx.obj.get("debug", False)
        m = ctx.obj.get("manager")
        logger.debug(f"debug={debug}")

        m.create_backup()

    return app
