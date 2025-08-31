from taskjournal.config import TEMPLATE_FORMAT


def wrap_with_format(text: str) -> str:
    """
    Wraps the given text with the appropriate opening and closing markers
    depending on the template format.

    Args:
        text (str): The text to wrap.

    Returns:
        str: The wrapped text.
    """
    fmt = TEMPLATE_FORMAT
    opening = " " if fmt == "txt" else "**"
    closing = "" if fmt == "txt" else "**"
    return f"{opening}{text}{closing}"
