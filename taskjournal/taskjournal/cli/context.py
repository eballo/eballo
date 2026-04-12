from datetime import datetime

from click.exceptions import Exit
from typer import Context

from taskjournal.services.logger import logger


def get_manager(ctx: Context):
    return ctx.obj["manager"]


def get_today(ctx: Context) -> datetime:
    return ctx.obj["today"]


def get_debug(ctx: Context) -> bool:
    return ctx.obj.get("debug", False)


def get_container(ctx: Context):
    return ctx.obj["container"]


_STRFTIME_TO_DISPLAY = {"%Y": "YYYY", "%m": "MM", "%d": "DD", "%H": "HH", "%M": "MM"}


def _display_fmt(fmt: str) -> str:
    for token, display in _STRFTIME_TO_DISPLAY.items():
        fmt = fmt.replace(token, display)
    return fmt


def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> datetime:
    """Parse a date string, raising a CLI-friendly error on failure."""
    try:
        return datetime.strptime(date_str, fmt)
    except ValueError:
        logger.error(f"❌ Invalid date format. Use '{_display_fmt(fmt)}'.")
        raise Exit(code=1)
