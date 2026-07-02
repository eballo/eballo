from logging import getLogger, DEBUG, INFO, Formatter

from rich.console import Console
from rich.logging import RichHandler

logger = getLogger("TaskTracker")
console = Console()


def configure_logging(debug: bool = False) -> None:
    level = DEBUG if debug else INFO
    logger.setLevel(level)
    if not any(isinstance(h, RichHandler) for h in logger.handlers):
        handler = RichHandler()
        handler.setLevel(level)
        formatter = Formatter(
            "%(asctime)s - %(name)s - %(message)s", datefmt="[%X]"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
