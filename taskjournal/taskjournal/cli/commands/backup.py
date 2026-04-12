from typer import Typer, Context

from taskjournal.cli.context import get_manager, get_debug
from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="Backup commands.",
        no_args_is_help=True,
    )

    @app.command(
        "run",
        help="Create a backup all files Examples:\n wk backup run\n",
    )
    def backup_run(ctx: Context) -> None:
        logger.debug(f"debug={get_debug(ctx)}")
        get_manager(ctx).create_backup()

    return app
