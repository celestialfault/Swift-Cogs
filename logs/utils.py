import discord
from enum import Enum

from redbot.core import RedContext
from redbot.core.config import Value, Group

from typing import Optional, Iterable, Tuple, Union

from redbot.core.utils.chat_formatting import info


class CheckType(Enum):
    BOTH = "both"
    AFTER = "after"
    BEFORE = "before"

    def __str__(self):
        return self.value


async def toggle(value: Value) -> bool:
    """Toggles a single Value object. This assumes that the Value is of a bool"""
    _val = await value()
    if not isinstance(_val, bool) and _val is not None:
        raise TypeError("Value object does not return a bool or None value")
    _val = not _val
    await value.set(_val)
    return _val


async def handle_group(ctx: RedContext, slots: list, types: Tuple[str], settings: Group, setting_type: str):
    if len(types) == 0:
        _settings = await settings()
        list1 = list(filter(None, _settings))
        list2 = list(filter(lambda x: not x, _settings))
        # Include items in `slots` that aren't in list1 or list2 in list2
        # So that they show up in the disabled category of status embeds
        list2 = list2 + [x for x in slots if x not in list1 and x not in list2]
        embed = status_embed(list1=list1, list2=list2, title="Current {} Log Settings".format(setting_type.title()))
        await ctx.send(embed=embed)
        return
    embed = await group_set(types, settings, slots)
    await ctx.send(info("Updated {} log settings".format(setting_type)), embed=embed)


async def group_set(set_items: Iterable[str], group: Group, slots: list = None) -> discord.Embed:
    """Group settings toggle"""
    slots = [x.lower() for x in slots or group.defaults]
    set_items = [x.lower() for x in set_items if x.lower() in slots]
    settings = await group()
    if not settings:
        settings = {x: False for x in slots}
    for item in slots:
        if item in set_items:
            settings[item] = not settings[item] if item in settings else True
        else:
            settings[item] = settings[item] if item in settings else False
    await group.set(settings)
    return status_embed([x for x in settings if settings[x]], [x for x in settings if not settings[x]])


def status_embed(list1: list, list2: list, title: str = discord.Embed.Empty) -> discord.Embed:
    embed = discord.Embed(colour=discord.Colour.blurple(), title=title)
    embed.add_field(name="Enabled", value=", ".join(list1 if list1 else ["None"]), inline=False)
    embed.add_field(name="Disabled", value=", ".join(list2 if list2 else ["None"]), inline=False)
    return embed


async def find_check(guildlog=None, **kwargs):
    if guildlog:
        check_type = CheckType(await guildlog.config.check_type())
    else:
        check_type = CheckType.AFTER

    checks = []

    if kwargs.get('after', None) and check_type in (CheckType.BOTH, CheckType.AFTER):
        checks.append(extract_check(kwargs.get('after')))
    if kwargs.get('before', None) and check_type in (CheckType.BOTH, CheckType.BEFORE):
        checks.append(extract_check(kwargs.get('before')))

    elif kwargs.get('created', None):
        checks.append(extract_check(kwargs.get('created')))
    elif kwargs.get('deleted', None):
        checks.append(extract_check(kwargs.get('deleted')))
    elif kwargs.get('member', None):
        checks.append(extract_check(kwargs.get('member')))

    return checks


def extract_check(obj) -> Optional[Union[discord.Member, discord.TextChannel, discord.Guild, discord.VoiceChannel]]:
    if isinstance(obj, discord.Message):
        return obj.author
    elif isinstance(obj, discord.VoiceState):
        return obj.channel
    elif isinstance(obj, discord.Guild) or isinstance(obj, discord.TextChannel) \
            or isinstance(obj, discord.VoiceChannel) or isinstance(obj, discord.Member):
        return obj
    else:
        return None
