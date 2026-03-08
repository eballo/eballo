from click import Context
from typer.core import TyperGroup


class GroupedHelpOrder(TyperGroup):
    desired_order = ["daily", "week", "month", "half-year", "retro", "backup"]

    def list_commands(self, ctx: Context) -> list[str]:
        cmds = list(self.commands.keys())
        ordered = [c for c in self.desired_order if c in self.commands]
        ordered += [c for c in cmds if c not in ordered]
        return ordered
