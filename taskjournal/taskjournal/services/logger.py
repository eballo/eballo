import logging
from rich.logging import RichHandler


def get_logger(name="TaskTracker"):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )
    return logging.getLogger(name)


logger = get_logger()
