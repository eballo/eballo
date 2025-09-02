import logging

from rich.logging import RichHandler

logger = logging.getLogger("TaskTracker")


def configure_logging(debug: bool = False):
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)
    if not any(isinstance(h, RichHandler) for h in logger.handlers):
        handler = RichHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(message)s", datefmt="[%X]"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
