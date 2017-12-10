from typing import Optional, Iterable

from redbot.core import RedContext
from redbot.core.config import Value, Group
from discord import Guild
from redbot.core.utils.chat_formatting import box

from .formatters import *

_guilds = {}


async def cmd_help(ctx: RedContext, cmd: str) -> None:
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()


async def toggle(value: Value) -> bool:
    _val = not await value()
    await value.set(_val)
    return _val


async def group_set(set_items: Iterable[str], group: Group, mapping: dict=None) -> str:
    if mapping:
        tmp = set_items
        set_items = []
        for item in tmp:
            set_items = mapping[item].lower() if item in mapping else item
    else:
        set_items = [x.lower() for x in set_items]
    async with group() as settings:
        defaults = group.defaults
        _settings = [(item, defaults[item]) for item in settings if item in defaults]
        settings = dict(_settings)
        # Loop through the options to set
        for item in defaults:
            settings[item] = item.lower() in set_items
        return await diff_box([x for x in settings if settings[x]],
                              [x for x in settings if not settings[x]])


async def diff_box(list1, list2) -> str:
    msg = "+ Enabled"
    msg += "\n"
    msg += ", ".join(list1 if list1 else ["None"])
    msg += "\n\n- Disabled\n"
    msg += ", ".join(list2 if list2 else ["None"])
    return box(msg, lang="diff")


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
