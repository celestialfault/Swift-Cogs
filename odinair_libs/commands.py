from typing import Optional

from discord.ext import commands
from redbot.core import RedContext
from redbot.core.utils.chat_formatting import pagify

__all__ = ('fmt', 'cmd_help', 'cmd_group')


async def fmt(ctx: RedContext, text: str, *args, delete_after: Optional[float] = None, **kwargs) -> None:
    for p in pagify(text.format(*args, **kwargs, prefix=ctx.prefix)):
        await ctx.send(p, delete_after=delete_after)


async def cmd_help(ctx: RedContext, cmd: str = "") -> None:
    """Sends sub-command help"""
    # This probably isn't the cleanest solution, but it works well enough,
    # so this is mostly what I'd consider "good enough"
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()


def cmd_group(name: str, *, parent=commands, **kwargs):
    # noinspection PyUnusedLocal
    async def _cmd(self, ctx: RedContext):
        await cmd_help(ctx, name)

    return parent.group(name=name, **kwargs)(_cmd)
