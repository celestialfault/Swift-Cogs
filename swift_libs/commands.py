from typing import Optional

from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify

__all__ = ("fmt", "cmd_help", "cmd_group")


async def fmt(
    ctx: commands.Context, text: str, *args, delete_after: Optional[float] = None, **kwargs
) -> None:
    for p in pagify(text.format(*args, **kwargs, prefix=ctx.prefix)):
        await ctx.send(p, delete_after=delete_after)


async def cmd_help(ctx: commands.Context, cmd: str = "") -> None:
    """Sends sub-command help"""
    # This probably isn't the cleanest solution, but it works well enough
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()


def cmd_group(name: str, *, parent=commands, **kwargs) -> commands.Group:
    """Dynamically create a simple command group

    You should really only add sub-command groups with this, and not root command groups.

    This means adding `test` to an existing `testing` command group is fine, but adding the root
    `testing` command group with this will just end in tears when you find out that it breaks
    [p]findcog in a way that I still have yet to try and find a way around.
    """
    # noinspection PyUnusedLocal
    async def _cmd(self, ctx: commands.Context):
        await cmd_help(ctx, name)

    return parent.group(name=name, **kwargs)(_cmd)
