import asyncio

import re

import discord
from discord.ext import commands

from redbot.core.bot import RedContext


async def ask_channel(ctx: RedContext, *channels: discord.abc.GuildChannel):
    """Prompt a user choice for a channel from a list of GuildChannel objects"""
    # Dear future adventurers:
    # Turn back while you still can
    if not hasattr(ctx, "guild"):  # Ensure this is called from a guild context
        return None
    bot = ctx.bot
    channels = [x for x in channels if getattr(x, "id", None) is not None]  # Remove channels without an id attribute
    _msg = ("More than one channel matches that name\n"
            "Please select which channel you'd like to use:\n\n"
            "{channels}\n\n"
            "Or type `cancel` to cancel".format(channels="\n".join(["**{}**: {}".format(channels.index(x) + 1,
                                                                                        x.mention)
                                                                    for x in channels])))
    msg = await ctx.send(_msg)

    async def ask():
        def check(message):
            return message.author.id == ctx.author.id and message.channel.id == ctx.channel.id

        try:
            msg_response = await bot.wait_for('message', check=check, timeout=30.0)
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


class GuildChannel(commands.IDConverter):
    async def convert(self, ctx, argument):
        if not hasattr(ctx, "guild"):
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
