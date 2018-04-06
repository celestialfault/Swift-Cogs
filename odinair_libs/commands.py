from typing import Optional

from redbot.core import RedContext

__all__ = ('fmt', 'cmd_help')


async def fmt(ctx: RedContext, text: str, delete_after: Optional[float] = None, *args, **kwargs) -> None:
    await ctx.send(text.format(*args, **kwargs, prefix=ctx.prefix), delete_after=delete_after)


async def cmd_help(ctx: RedContext, cmd: str = "") -> None:
    """Sends sub-command help"""
    # This probably isn't the cleanest solution, but it works well enough,
    # so this is mostly what I'd consider "good enough"
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()
