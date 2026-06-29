from typer import Typer, Context, Option

from taskjournal.cli.context import get_manager, get_today, get_debug
from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="1on1 reporting commands.",
        no_args_is_help=True,
    )

    @app.command(
        "report",
        help="Create a 1on1 report.\n\nExamples:\n  wk 1on1 report\n",
    )
    def one_on_one_report(
        ctx: Context,
    ) -> None:
        logger.debug(f"debug={get_debug(ctx)}")
        get_manager(ctx).create_one_on_one(get_today(ctx))

    @app.command(
        "add-topic",
        help=(
            "Add a topic to the next 1on1 session without opening the file.\n\n"
            "Examples:\n"
            "  wk 1on1 add-topic -t 'Discuss Q3 career plan'\n"
            "  wk 1on1 add-topic -t 'Blocker with prod access'\n"
        ),
    )
    def add_topic(
        ctx: Context,
        topic: str = Option(..., "--topic", "-t", help="Topic to add."),
    ) -> None:
        today = get_today(ctx)
        try:
            get_manager(ctx).add_topic_to_one_on_one(today, topic)
            logger.info(f"Added topic: {topic}")
        except (FileNotFoundError, ValueError) as e:
            logger.error(str(e))

    return app
