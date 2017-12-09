from typing import Optional

from redbot.core import RedContext
from redbot.core.config import Value, Group
from discord import Guild

from .formatters import *

_guilds = {}


async def cmd_help(ctx: RedContext, cmd: str):
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()


async def toggle(value: Value):
    _val = not await value()
    await value.set(_val)
    return _val


async def diff_box(list1, list2):
    msg = "```diff\n"
    msg += "+ Enabled"
    msg += "\n"
    msg += ", ".join(list1)
    msg += "\n\n- Disabled\n"
    msg += ", ".join(list2)
    msg += "\n```"
    return msg


async def set_formatter(format_type: str, config_val: Value, guild: Guild):
    await config_val.set(format_type)
    if guild.id in _guilds:
        del _guilds[guild.id]


async def get_formatter(guild: Guild, config: Group) -> Optional[FormatterBase]:
    if guild.id in _guilds:
        return _guilds[guild.id]
    else:
        _format = await config.format()
        if _format == "TEXT":
            cls = TextFormatter
        elif _format == "EMBED":
            cls = EmbedFormatter
        else:
            _guilds[guild.id] = None
            return None
        formatter = cls(guild=guild)
        _guilds[guild.id] = formatter
        return formatter
