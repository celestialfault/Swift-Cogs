import discord
from enum import Enum

from redbot.core import RedContext
from redbot.core.config import Group

from typing import Optional, Union, Dict, Sequence, List

from redbot.core.utils.chat_formatting import warning

from odinair_libs.config import group_toggle
from odinair_libs.formatting import tick


__all__ = ["CheckType", "handle_group", "status_embed", "find_check"]


class CheckType(Enum):
    BOTH = "both"
    AFTER = "after"
    BEFORE = "before"

    def __str__(self):
        return self.value


async def handle_group(ctx: RedContext, slots: Sequence[str], types: Sequence[str], settings: Group, setting_type: str,
                       descriptions: Dict[str, str] = None):
    if len(types) == 0:
        await ctx.send(embed=status_embed(settings={**{x: False for x in slots}, **await settings()},
                                          title="Current {} Log Settings".format(setting_type.title()),
                                          descriptions=descriptions))
        return
    try:
        settings = await group_toggle(group=settings, toggle_keys=types, slots=slots, strict_slots=True)
    except KeyError as e:
        await ctx.send(warning("'{0!s}' is not an available setting".format(e)))
        return
    embed = status_embed(settings=settings, title="{} Log Settings".format(setting_type.title()),
                         descriptions=descriptions)
    await ctx.send(tick("Updated {} log settings".format(setting_type)), embed=embed)


def add_descriptions(items: List[str], descriptions: Dict[str, str] = None) -> str:
    if descriptions is None:
        descriptions = {}
    for item in items:
        index = items.index(item)
        items[index] = "**{}** — {}".format(item, descriptions.get(item, "No description set"))
    return "\n".join(items)


def status_embed(settings: Dict[str, bool], descriptions: Dict[str, str] = None,
                 title: str = discord.Embed.Empty) -> discord.Embed:
    enabled = [x for x in settings if settings[x]] or None
    disabled = [x for x in settings if not settings[x]] or None

    if enabled is not None:
        enabled = add_descriptions(enabled, descriptions)
    else:
        enabled = "**None** — All of these settings are disabled"

    if disabled is not None:
        disabled = add_descriptions(disabled, descriptions)
    else:
        disabled = "**None** — All of these settings are enabled"

    embed = discord.Embed(colour=discord.Colour.blurple(), title=title,
                          description="**❯ Enabled Log Settings**\n{}\n\n"
                                      "**❯ Disabled Log Settings**\n{}"
                                      "".format(enabled, disabled))
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
