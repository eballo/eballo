from time import sleep, monotonic

from rich.live import Live
from rich.text import Text


def run_marquee(text: str, style: str = "bold green", duration: float = 3.0) -> None:
    padded = f"   {text}   "
    width = 60
    pos = 0

    with Live(transient=True, refresh_per_second=20) as live:
        start = monotonic()
        while monotonic() - start < duration:
            visible = (padded * 3)[pos : pos + width]
            live.update(Text(visible, style=style))
            pos = (pos + 1) % len(padded)
            sleep(0.05)
