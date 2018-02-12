import asyncio
from typing import Union, Optional

from collections import OrderedDict
from datetime import timedelta

import re

import discord
from discord.ext import commands

from redbot.core.bot import RedContext

from odinair_libs.formatting import td_format


def get_role_or_member(snowflake: int, guild: discord.Guild):
    return guild.get_member(snowflake) or discord.utils.get(guild.roles, id=snowflake)


async def ask_channel(ctx: RedContext, *channels: discord.abc.GuildChannel):
    """Prompt a user choice for a channel from a list of GuildChannel objects"""
    # Dear future adventurers:
    # Turn back while you still can
    if not hasattr(ctx, "guild"):  # Ensure this is called from a guild context
        return None
    bot = ctx.bot
    channels = [x for x in channels if hasattr(x, "id")]  # Remove channels without an id attribute
    _msg = ("More than one channel matches that name\n"
            "Please select which channel you'd like to use:\n\n"
            "{channels}\n\n"
            "Or type `cancel` to cancel".format(channels="\n".join(["**{}**: {}".format(channels.index(x) + 1,
                                                                                        x.mention)
                                                                    for x in channels])))
    msg = await ctx.send(_msg)

    async def ask():
        try:
            msg_response = await bot.wait_for('message',
                                              check=lambda message: message.author.id == ctx.author.id
                                                                    and message.channel.id == ctx.channel.id,
                                              timeout=30.0)
        except asyncio.TimeoutError:
            return None
        return msg_response

    channel = None
    response = None
    while channel is None:
        response = await ask()

        if response is not None:
            if response.content.lower() == "cancel":
                break
            try:
                channel_id = int(response.content)
                if channel_id < 1 or channel_id > len(channels):
                    if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                        await response.delete()
                        response = None
                    await ctx.send("Please select a channel index between **1** and **{}**".format(len(channels)),
                                   delete_after=10.0)
                    continue
                channel = channels[channel_id - 1]
            except (ValueError, IndexError):
                if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                    await response.delete()
                    response = None
                continue
        else:
            break

    # Try to cleanup the response if we have permissions to do so
    if response is not None and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
        await ctx.channel.delete_messages([response, msg])
    else:
        await msg.delete()

    return getattr(channel, "id", None)


class FutureTime(commands.Converter):
    # The following variables, including `get_seconds`, is originally taken from ZeLarpMaster's Reminders cog
    # https://github.com/ZeLarpMaster/ZeCogs/blob/master/reminder/reminder.py
    # The following changes have been made from the original source:
    #  - Changed TIME_QUANTITIES to use timedeltas, to be more consistent with td_format
    #  - Added float support, meaning time periods like '0.5h' are accepted,
    #    and converted as if it was given as '30m'
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
    STRICT_MODE = False

    def __init__(self, max_duration: Union[str, int, float, None] = "2y", strict: bool = False):
        """Create a FutureTime converter

        Parameters
        -----------

            max_duration: Union[str, int, float, None]

                How long in seconds to allow for a conversion to go up to. Set to None to disable this

            strict: bool

                If this is True, `convert` will throw a `commands.BadArgument` exception
                if the argument passed fails to convert into a timedelta, such as if
                the user only gave invalid time strings
        """
        self.MAX_SECONDS = self.get_seconds(max_duration) if isinstance(max_duration, str) else max_duration
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
            raise commands.BadArgument('Time duration exceeds {}'
                                       .format(td_format(timedelta(seconds=self.MAX_SECONDS))))
        if seconds is None and self.STRICT_MODE:
            raise commands.BadArgument("Failed to parse duration")
        return timedelta(seconds=seconds) if seconds else None


TimeDuration = FutureTime


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
                            raise commands.BadArgument("Cannot find channel `{}`".format(argument))
                    else:
                        cid = channels_matched[0].id
            else:  # get the channel id from the mention
                cid = int(match.group(1))

        if cid:
            return guild.get_channel(cid)
        raise commands.BadArgument("Cannot find channel `{}`".format(argument))
