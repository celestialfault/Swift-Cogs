import re
from datetime import timedelta

import discord
from discord.ext import commands

from redbot.core import RedContext
from redbot.core.config import Value, Group

from typing import Optional, Iterable, Tuple, Union

from redbot.core.utils.chat_formatting import info


class GuildChannel(commands.IDConverter):
    # noinspection PyShadowingNames
    async def convert(self, ctx, argument):
        guild = ctx.guild
        cid = None
        match = self._get_id_match(argument) or re.match(r'<#!?([0-9]+)>$', argument)

        if match is None:  # not a channel mention
            for channel in guild.channels:
                if str(channel.name).lower() == argument.lower():
                    cid = channel.id
                    break

        else:
            try:
                cid = int(str(argument).strip("<#>"))
            except ValueError:
                raise commands.BadArgument("Cannot parse channel mention `{}`".format(argument))

        if cid:
            return guild.get_channel(cid)
        raise commands.BadArgument("Cannot find channel `{}`".format(argument))


async def cmd_help(ctx: RedContext, cmd: str) -> None:
    """Sends sub-command help

    This mostly exists because I don't want to re-write these two lines for about ten different functions"""
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()


async def toggle(value: Value) -> bool:
    """Toggles a single Value object. This assumes that the Value is of a bool"""
    # Parameter self is unfilled :Thinkies:
    # noinspection PyArgumentList
    _val = await value()
    if not isinstance(_val, bool) and _val is not None:
        raise TypeError("Value object does not return a bool or None value")
    _val = not _val
    await value.set(_val)
    return _val


async def handle_group(ctx: RedContext, slots: list, types: Tuple[str], settings: Group, setting_type: str):
    if len(types) == 0:
        # noinspection PyArgumentList
        _settings = await settings()
        embed = await status_embed(list1=[x for x in _settings if _settings[x]],
                                   list2=[x for x in _settings if not _settings[x]],
                                   title="{} Logging".format(setting_type.title()))
        await ctx.send(embed=embed)
        return
    embed = await group_set(types, settings, slots)
    await ctx.send(info("Updated {} log settings".format(setting_type)), embed=embed)


async def group_set(set_items: Iterable[str], group: Group, slots: list = None) -> discord.Embed:
    """Group settings toggle"""
    slots = [x.lower() for x in slots or group.defaults]
    set_items = [x.lower() for x in set_items if x.lower() in slots]
    # noinspection PyArgumentList
    settings = await group()
    for item in slots:
        if item in set_items:
            settings[item] = not settings[item] if item in settings else True
        else:
            settings[item] = settings[item] if item in settings else False
    await group.set(settings)
    return await status_embed([x for x in settings if settings[x]], [x for x in settings if not settings[x]])


async def status_embed(list1: list, list2: list, title: str = discord.Embed.Empty) -> discord.Embed:
    embed = discord.Embed(colour=discord.Colour.blurple(), title=title)
    embed.add_field(name="Enabled", value=", ".join(list1 if list1 else ["None"]), inline=False)
    embed.add_field(name="Disabled", value=", ".join(list2 if list2 else ["None"]), inline=False)
    return embed


# ~~stolen~~ borrowed from StackOverflow
# https://stackoverflow.com/a/13756038
def td_format(td_object: timedelta) -> str:
    seconds = int(td_object.total_seconds())
    periods = [
        ('year', 60 * 60 * 24 * 365),
        ('month', 60 * 60 * 24 * 30),
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value == 1:
                strings.append("%s %s" % (period_value, period_name))
            else:
                strings.append("%s %ss" % (period_value, period_name))

    return ", ".join(strings)


def difference(list1: Iterable, list2: Iterable, *, check_val: bool = False) -> Tuple[list, list]:
    """Returns a tuple of lists based on the Iterable items passed in

    If check_val is True, this checks for True-ish items"""
    if check_val:
        # Only include items that evaluate to True
        list1 = [x for x, val in list1 if val]
        list2 = [x for x, val in list2 if val]

    added = [x for x in list2 if x not in list1]
    removed = [x for x in list1 if x not in list2]
    return added, removed


def normalize(text, *, title_case: bool = True, **kwargs):
    text = str(text)
    text = text.replace("_", " ")
    for item in kwargs:
        text = text.replace(item, kwargs[item])
    if title_case:
        text = text.title()
    return text


def find_check(**kwargs) -> Optional[Union[discord.Member, discord.TextChannel, discord.Guild]]:
    if kwargs.get('after', None):
        return extract_check(kwargs.get('after'))
    elif kwargs.get('created', None):
        return extract_check(kwargs.get('created'))
    elif kwargs.get('deleted', None):
        return extract_check(kwargs.get('deleted'))
    else:
        return None


def extract_check(obj) -> Optional[Union[discord.Member, discord.TextChannel, discord.Guild]]:
    if isinstance(obj, discord.Member):
        return obj
    elif isinstance(obj, discord.Message):
        return obj.author
    elif isinstance(obj, discord.Guild):
        return obj
    elif isinstance(obj, discord.TextChannel):
        return obj
    else:
        return None
