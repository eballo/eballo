from typer import Argument, Context, Typer

from taskjournal.cli.context import get_manager, get_today
from taskjournal.services.logger import logger


def build_app() -> Typer:
    app = Typer(
        help="Append a quick note to today's Notes section.",
        no_args_is_help=True,
        invoke_without_command=True,
    )

    @app.callback(invoke_without_command=True)
    def note_add(
        ctx: Context,
        text: str = Argument(..., help="Note text to append."),
    ) -> None:
        """Append a timestamped note to today's daily file without opening it."""
        if ctx.invoked_subcommand is not None:
            return
        m = get_manager(ctx)
        today = get_today(ctx)
        try:
            m.add_note_to_daily(today, text)
        except (FileNotFoundError, ValueError) as e:
            logger.error(str(e))
            raise SystemExit(1)

    return app
