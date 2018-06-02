from typing import Optional, Type

from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify

__all__ = ("fmt", "cmd_help", "cmd_group", "resolve_any")


async def fmt(
    ctx: commands.Context, text: str, *args, delete_after: Optional[float] = None, **kwargs
) -> None:
    """Format the given string and send it"""
    for p in pagify(text.format(*args, **kwargs, prefix=ctx.prefix)):
        await ctx.send(p, delete_after=delete_after)


async def cmd_help(ctx: commands.Context, cmd: str = "") -> None:
    """Sends sub-command help"""
    # This probably isn't the cleanest solution, but it works well enough
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()


def cmd_group(name: str, *, parent=commands, **kwargs) -> commands.Group:
    """Dynamically create a simple command group

    This is technically a Really Bad Idea™, and you should probably just create a command method
    that calls `cmd_help` instead of using this.

    But if you do choose to use this, then please be aware that this works in such a way that
    `[p]findcog` won't properly function on root command groups, and as such this should only
    be used for sub-groups.
    """
    # noinspection PyUnusedLocal
    async def _cmd(self, ctx: commands.Context):
        await cmd_help(ctx, name)

    return parent.group(name=name, **kwargs)(_cmd)


# noinspection PyPep8Naming
class undefined:
    pass


undefined = undefined()


async def resolve_any(ctx: commands.Context, argument: str, *converters: Type[commands.Converter]):
    resolved = undefined
    for converter in converters:
        try:
            resolved = await converter().convert(ctx, argument)
        except commands.BadArgument:
            pass
        else:
            break
    if resolved is undefined:
        raise commands.BadArgument(
            "The given argument could not be converted to any supported type"
        )
    return resolved
