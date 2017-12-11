from typing import Optional, Iterable, Tuple

from redbot.core import RedContext
from redbot.core.config import Value, Group
from discord import Guild
from redbot.core.utils.chat_formatting import box

from .formatters import *

_guilds = {}  # Formatter cache


async def cmd_help(ctx: RedContext, cmd: str) -> None:
    """Sends sub-command help

    This mostly exists because I don't want to re-write these two lines for about ten different functions"""
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()


async def toggle(value: Value) -> bool:
    """Toggles a single Value object. This assumes that the Value is of a bool"""
    _val = not await value()
    await value.set(_val)
    return _val


async def group_set(set_items: Iterable[str], group: Group, slots: list = None) -> Tuple[bool, str]:
    """Group toggle. Preserves currently-set values if they aren't specified in set_items"""
    # dear future adventurers: there be dragons here
    # (turn back while you still can)
    slots = [x.lower() for x in slots or group.defaults]
    set_items = [x.lower() for x in set_items if x.lower() in slots]
    settings = await group()
    _settings = dict(settings)
    for item in slots:
        if item in set_items:
            settings[item] = not settings[item] if item in settings else True
        else:
            settings[item] = settings[item] if item in settings else False
    await group.set(settings)
    return _settings != settings, await diff_box([x for x in settings if settings[x]],
                                                 [x for x in settings if not settings[x]])


async def diff_box(list1, list2) -> str:
    """Returns the two lists in a box with Enabled and Disabled headers respectively"""
    msg = "+ Enabled"
    msg += "\n"
    msg += ", ".join(list1 if list1 else ["None"])
    msg += "\n\n- Disabled\n"
    msg += ", ".join(list2 if list2 else ["None"])
    return box(msg, lang="diff")


async def set_formatter(format_type: str, config_val: Value, guild: Guild):
    """Set the format type for the specified guild"""
    await config_val.set(format_type)
    if guild.id in _guilds:
        del _guilds[guild.id]


async def get_formatter(guild: Guild, config: Group) -> Optional[FormatterBase]:
    """Get the formatter for the specified guild"""
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
