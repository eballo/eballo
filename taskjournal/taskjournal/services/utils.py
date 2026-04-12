from taskjournal.config import TEMPLATE_FORMAT


class FormatUtils:

    @staticmethod
    def wrap_with_format(text: str) -> str:
        """
        Wraps the given text with the appropriate opening and closing markers
        depending on the template format.
        """
        fmt = TEMPLATE_FORMAT
        opening = " " if fmt == "txt" else "**"
        closing = "" if fmt == "txt" else "**"
        return f"{opening}{text}{closing}"
