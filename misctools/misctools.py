import unicodedata
from datetime import datetime

from textwrap import dedent
from inspect import getsource

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import warning, pagify
from redbot.core.i18n import CogI18n

from cog_shared.odinair_libs import td_format

_ = CogI18n("MiscTools", __file__)


class MiscTools:
    """A somewhat basic collection quick & dirty utilities

    This is mostly only useful for making cogs, or working with the Discord API.
    """

    __author__ = "odinair <odinair@odinair.xyz>"

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    async def rtfs(self, ctx: RedContext, *, command_name: str):
        """Get the source for a command or sub command"""
        command = self.bot.get_command(command_name)
        if command is None:
            await ctx.send(warning(_("That command doesn't exist")))
            return
        await ctx.send_interactive(pagify(dedent(getsource(command.callback)), shorten_by=10), box_lang="py")

    @commands.command()
    async def charinfo(self, ctx: RedContext, *, characters: str):
        """Get the unicode name for characters

        Up to 25 characters can be given at one time
        """
        if len(characters) > 25:
            await ctx.send_help()
            return

        def convert(c):
            return "{} \N{EM DASH} {}".format(c, unicodedata.name(c, 'Name not found'))

        await ctx.send("\n".join(map(convert, characters)))

    @commands.command(aliases=["pingt"])
    async def pingtime(self, ctx: RedContext):
        """Get the time it takes the bot to respond to a command

        This is by no means fully accurate, and should be treated similarly to rough estimate

        Time to command execution means how long it took for the bot to receive the command message
        and execute the command
        """
        time_to_execution = td_format(datetime.utcnow() - ctx.message.created_at, milliseconds=True)
        now = datetime.utcnow()
        await ctx.trigger_typing()
        time_to_typing = td_format(datetime.utcnow() - now, milliseconds=True)
        full_round_trip = td_format(datetime.utcnow() - ctx.message.created_at, milliseconds=True)
        await ctx.send(_("\N{TABLE TENNIS PADDLE AND BALL} Pong!\n"
                         "Time to command execution: {}\n"
                         "Typing indicator: {}\n\n"
                         "Full round trip: {}").format(time_to_execution, time_to_typing, full_round_trip))

    @commands.command(aliases=["snowflake"])
    async def snowflaketime(self, ctx: RedContext, *snowflakes: int):
        """Retrieve when one or more snowflake IDs were created at"""
        if not snowflakes:
            await ctx.send_help()
            return
        strs = []
        for snowflake in snowflakes:
            snowflake_time = discord.utils.snowflake_time(snowflake)
            strs.append("{}: `{}` \N{EM DASH} {}"
                        .format(snowflake, snowflake_time.strftime('%A %B %d, %Y at %X UTC'),
                                td_format(snowflake_time - datetime.utcnow(), append_str=True)))
        await ctx.send_interactive(pagify("\n".join(strs)))
