from os import walk
from os.path import isdir, isfile, join

from typer import Typer, Context, Argument

from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="Migration commands.",
        no_args_is_help=True,
    )

    @app.command(
        "daily",
        help="Migrate old txt daily notes to md format.\n\nExamples:\n  wk migrate daily .\n  wk migrate daily 2025/week17/2025-04-22-DailyNotes.txt",
    )
    def migrate_daily(
        ctx: Context,
        path: str = Argument(..., help="File path or Directory path to migrate"),
    ) -> None:
        debug = ctx.obj.get("debug", False)
        logger.debug(f"debug={debug}, path={path}")

        container = ctx.obj.get("container")
        service = container.migration()

        if isfile(path):
            service.migrate_file(path)
        elif isdir(path):
            logger.info(f"Scanning directory: {path}")
            for root, _, files in walk(path):
                for file in files:
                    if file.endswith("DailyNotes.txt"):
                        full_path = join(root, file)
                        service.migrate_file(full_path)
        else:
            logger.error(f"Path not found: {path}")

        # Show migration summary
        service.migration_info()

    return app
