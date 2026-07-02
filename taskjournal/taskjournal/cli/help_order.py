from click import Context as ClickContext, HelpFormatter
from rich.text import Text
from typer.core import TyperGroup

from taskjournal.cli import version as _version
from taskjournal.services.logger import console

_BANNER = Text(
    "ooooooooooooo                    oooo        \n"
    "8'   888   `8                    `888        \n"
    "     888       .oooo.    .oooo.o  888  oooo  \n"
    "     888      `P  )88b  d88(  \"8  888 .8P'   \n"
    "     888       .oP\"888  `\"Y88b.   888888.    \n"
    "     888      d8(  888  o.  )88b  888 `88b.  \n"
    "    o888o     `Y888\"\"8o 8\"\"888P' o888o o888o \n"
    "                                             \n"
    "   oooo                                                      oooo  \n"
    "   `888                                                      `888  \n"
    "    888  .ooooo.  oooo  oooo  oooo d8b ooo. .oo.    .oooo.    888  \n"
    "    888 d88' `88b `888  `888  `888\"\"8P `888P\"Y88b  `P  )88b   888  \n"
    "    888 888   888  888   888   888      888   888   .oP\"888   888  \n"
    "    888 888   888  888   888   888      888   888  d8(  888   888  \n"
    ".o. 88P `Y8bod8P'  `V88V\"V8P' d888b    o888o o888o `Y888\"\"8o o888o\n"
    "`Y888P                                                             ",
    style="cyan",
    no_wrap=True,
)


class GroupedHelpOrder(TyperGroup):
    desired_order = ["daily", "week", "month", "half-year", "retro", "1on1", "holidays", "statistics", "info"]

    def list_commands(self, ctx: ClickContext) -> list[str]:  # type: ignore[override]
        cmds = list(self.commands.keys())
        ordered = [c for c in self.desired_order if c in self.commands]
        ordered += [c for c in cmds if c not in ordered]
        return ordered

    def format_help(self, ctx: ClickContext, formatter: HelpFormatter) -> None:
        console.print(_BANNER, no_wrap=True, crop=False, highlight=False)
        console.print(f"[dim]v{_version}[/dim]")
        console.print()
        super().format_help(ctx, formatter)
