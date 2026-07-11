from random import choice
from time import sleep

from httpx import get as http_get, TimeoutException, RequestError
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live
from typer import Typer

from taskjournal.services.logger import console

_JOKE_API = "https://v2.jokeapi.dev/joke/Any?safe-mode&blacklistFlags=nsfw,racist,sexist,explicit"

_FALLBACK_JOKES: list[tuple[str, str]] = [
    (
        "Why do programmers prefer dark mode?",
        "Because light attracts bugs!",
    ),
    (
        "How many programmers does it take to change a light bulb?",
        "None — it's a hardware problem.",
    ),
    (
        "Why do Java developers wear glasses?",
        "Because they don't C#.",
    ),
    (
        "A SQL query walks into a bar, walks up to two tables and asks...",
        '"Can I join you?"',
    ),
    (
        "Why did the developer go broke?",
        "Because he used up all his cache.",
    ),
    (
        "What's a programmer's favourite hangout place?",
        "Foo Bar.",
    ),
    (
        "Why do functions smell good?",
        "Because they have good scoping.",
    ),
    (
        "I had a joke about recursion...",
        "I had a joke about recursion... I had a joke about recursion...",
    ),
    (
        "What do you call a programmer from Finland?",
        "Nerdic.",
    ),
    (
        "Debugging: being the detective in a crime movie...",
        "...where you are also the murderer.",
    ),
]


def _fetch_joke() -> tuple[str, str] | None:
    try:
        response = http_get(_JOKE_API, timeout=5.0)
        data = response.json()
        if data.get("type") == "twopart":
            return data["setup"], data["delivery"]
        if data.get("type") == "single":
            joke = data.get("joke", "")
            if joke:
                return joke, ""
    except (TimeoutException, RequestError, KeyError, ValueError):
        pass
    return None


def build_app() -> Typer:
    app = Typer(
        help="Display a random joke.",
        no_args_is_help=False,
        invoke_without_command=True,
    )

    @app.callback(invoke_without_command=True)
    def joke() -> None:
        result = _fetch_joke()
        if result is None:
            result = choice(_FALLBACK_JOKES)

        setup, punchline = result

        if punchline:
            console.print(Panel(f"🎭  {setup}", expand=False))
            with Live(Spinner("dots", text="  ..."), transient=True, refresh_per_second=10):
                sleep(1.5)
            console.print(Panel(f"    {punchline}", expand=False))
        else:
            console.print(Panel(f"🎭  {setup}", expand=False))

    return app
