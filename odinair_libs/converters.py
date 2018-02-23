from typing import Union, Optional, Sequence

from collections import OrderedDict
from datetime import timedelta

import re

import discord
from discord.ext import commands

from redbot.core.bot import RedContext

from odinair_libs.formatting import td_format
from odinair_libs.menus import paginate, MenuResult

__all__ = ["GuildChannel", "FutureTime", "chunks", "get_role_or_member"]


def chunks(l, n):  # https://stackoverflow.com/a/312464
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def get_role_or_member(snowflake: int, guild: discord.Guild):
    return guild.get_member(snowflake) or discord.utils.get(guild.roles, id=snowflake)


async def ask_channel(ctx: RedContext, *channels: discord.abc.GuildChannel, message: str = None):
    """Prompt a user choice for a channel from a list of GuildChannel objects"""
    if not hasattr(ctx.message, "guild"):  # Ensure this is called from a guild context
        return None
    channels = [x for x in channels if hasattr(x, "id")]  # Remove channels without an id attribute
    if len(channels) == 1:
        return channels[0]
    elif len(channels) == 0:
        return None

    actions = {
        "one": "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}",
        "two": "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}",
        "three": "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}",
        "four": "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}",
        "cancel": "\N{CROSS MARK}"
    }
    channels = list(chunks(channels, 4))

    emojis = ["\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}",
              "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}", "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}"]

    if message is None:
        message = "One or more of those channels matches that name.\nPlease select which channel you'd like to use:"

    # noinspection PyShadowingNames
    def build_page(page: Sequence[discord.abc.GuildChannel]) -> str:
        def ctype(x):
            return (
                "\N{SPIRAL NOTE PAD}" if isinstance(x, discord.TextChannel) else
                "\N{SPEAKER}" if isinstance(x, discord.VoiceChannel) else
                "\N{FILE FOLDER}"
            )

        channels__ = [f"{emojis[page.index(x)]} {ctype(x)} {x.mention}" for x in page]

        channels__ = "\n".join(channels__)
        return f"{message}\n\n{channels__}"

    # noinspection PyTypeChecker
    result = MenuResult(menu=None, timed_out=False, action=None)
    page = channels[0]
    while True:
        result, page = await paginate(ctx, channels, actions=actions, page_converter=build_page,
                                      colour=getattr(ctx.me, "colour", discord.Embed.Empty), message=result.message,
                                      page=channels.index(page))
        if result.timed_out is True or result.action == "cancel":
            channel = None
            break
        if result.action in ("one", "two", "three", "four"):
            action = (
                0 if result == "one" else
                1 if result == "two" else
                2 if result == "three" else
                3 if result == "four" else None
            )
            try:
                channel = page[action]
            except IndexError:
                continue
            break

    try:
        await result.message.delete()
    except (discord.HTTPException, AttributeError):
        pass
    return getattr(channel, "id", None)


class FutureTime(commands.Converter):
    # The following variables, including `get_seconds`, is originally taken from ZeLarpMaster's Reminders cog
    # https://github.com/ZeLarpMaster/ZeCogs/blob/master/reminder/reminder.py
    # The following changes have been made from the original source:
    #  - Changed TIME_QUANTITIES to use timedeltas, to be more consistent with td_format
    #  - Added float support, meaning values similar to '0.5h' are accepted,
    #    and converted as if they were given as '30m'
    #  - Properly handle spaces between the duration and time period
    #  - Ported to a proper Converter
    TIME_AMNT_REGEX = re.compile("([0-9]+\.?[0-9]*) ?([a-z]+)", re.IGNORECASE)
    TIME_QUANTITIES = OrderedDict([("seconds", 1), ("minutes", 60),
                                   ("hours", timedelta(hours=1).total_seconds()),
                                   ("days", timedelta(days=1).total_seconds()),
                                   ("weeks", timedelta(days=7).total_seconds()),
                                   ("months", timedelta(days=30).total_seconds()),
                                   ("years", timedelta(days=365).total_seconds())])
    MAX_SECONDS = TIME_QUANTITIES["years"] * 2
    MIN_SECONDS = None
    STRICT_MODE = False

    def __init__(self,
                 max_duration: Union[str, int, float, None] = "2y",
                 min_duration: Union[str, int, float, None] = None,
                 strict: bool = False):
        """Create a FutureTime converter

        Parameters
        -----------
        max_duration: Union[str, int, float, None]
            How long in seconds to allow for a conversion to go up to. Set to None to disable this

            Defaults to ``"2y"``
        min_duration: Union[str, int, float, None]
            The minimum duration that can be parsed.
            Setting this to 0 effectively acts as if this was set to None

            Defaults to ``None``
        strict: bool
            If this is True, `convert` will throw a `commands.BadArgument` exception
            if the argument passed fails to convert into a timedelta, such as if
            the user only gave invalid time strings

            Time durations that fail to pass either max or min durations will always throw a BadArgument exception

            Defaults to ``False``
        """
        self.MAX_SECONDS = self.get_seconds(max_duration) if isinstance(max_duration, str) else max_duration
        self.MIN_SECONDS = self.get_seconds(min_duration) if isinstance(min_duration, str) else min_duration
        self.STRICT_MODE = strict

    @staticmethod
    def get_seconds(time: str) -> Optional[int]:
        """Returns the amount of converted time or None if invalid"""
        seconds = 0
        for time_match in FutureTime.TIME_AMNT_REGEX.finditer(time):
            time_amnt = float(time_match.group(1))
            time_abbrev = time_match.group(2)
            time_quantity = discord.utils.find(lambda t: t[0].startswith(time_abbrev),
                                               FutureTime.TIME_QUANTITIES.items())
            if time_quantity is not None:
                seconds += time_amnt * time_quantity[1]
        return None if seconds == 0 else seconds

    async def convert(self, ctx, argument: str) -> Union[None, timedelta]:
        seconds = self.get_seconds(argument)

        if seconds and self.MAX_SECONDS is not None and seconds > self.MAX_SECONDS:
            raise commands.BadArgument('Time duration exceeds {}'.format(
                td_format(timedelta(seconds=self.MAX_SECONDS))))
        elif seconds and self.MIN_SECONDS is not None and seconds < self.MIN_SECONDS:
            raise commands.BadArgument('Time duration does not exceed minimum of {}'.format(
                td_format(timedelta(seconds=self.MIN_SECONDS))))

        if seconds is None and self.STRICT_MODE:
            raise commands.BadArgument("Failed to parse duration")
        return timedelta(seconds=seconds) if seconds else None


class GuildChannel(commands.IDConverter):
    # Yes, it would have been quicker to specify all the channel types similar to
    # 'discord.TextChannel or discord.VoiceChannel or discord.CategoryChannel' instead of making this,
    # but let's be honest, that isn't as fun (and it also looks objectively worse than just specifying one converter)
    async def convert(self, ctx, argument):
        if not getattr(ctx, "guild", None):
            raise commands.BadArgument("This must be ran in a guild context")
        guild = ctx.guild
        cid = None
        match = self._get_id_match(argument) or re.match(r'<#!?([0-9]+)>$', argument)

        try:  # channel id parse attempt
            cid = int(argument)
        except ValueError:
            if match is None:  # not a channel mention
                channels_matched = [x for x in guild.channels if x.name.lower() == argument.lower()]
                if any(channels_matched):
                    if len(channels_matched) > 1:
                        cid = await ask_channel(ctx, *channels_matched)
                        if cid is None:
                            raise commands.BadArgument(f"Cannot find channel {argument}")
                    else:
                        cid = channels_matched[0].id
            else:  # get the channel id from the mention
                cid = int(match.group(1))

        if cid:
            return guild.get_channel(cid)
        raise commands.BadArgument(f"Cannot find channel {argument}")
