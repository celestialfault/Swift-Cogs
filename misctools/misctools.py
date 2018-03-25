import unicodedata
from datetime import datetime

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import warning, pagify
from redbot.core.i18n import CogI18n

from cog_shared.odinair_libs.formatting import td_format, get_source

_ = CogI18n("MiscTools", __file__)


class MiscTools:
    """Various quick & dirty utilities
    Mostly useful when making cogs, and/or for advanced server administration use.
    """

    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = "1.0.0"

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    async def rtfs(self, ctx: RedContext, *, command_name: str):
        """Get the source for a command or sub command"""
        command = self.bot.get_command(command_name)
        if command is None:
            await ctx.send(warning(_("That command doesn't exist")))
            return
        await ctx.send_interactive(pagify(get_source(command.callback), shorten_by=10), box_lang="py")

    @commands.command()
    async def charinfo(self, ctx: RedContext, *, characters: str):
        """Get the unicode name for characters

        Up to 25 characters can be given at one time
        """
        if len(characters) > 25:
            await ctx.send_help()
            return

        def convert(c):
            return f"{c} \N{EM DASH} {unicodedata.name(c, 'Name not found')}"

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

    @commands.command(aliases=["snowflaketime"])
    async def snowflake(self, ctx: RedContext, *snowflakes: int):
        """Get the time that one or more snowflake IDs were created at"""
        if not snowflakes:
            await ctx.send_help()
            return
        strs = []
        for snowflake in snowflakes:
            snowflake_time = discord.utils.snowflake_time(snowflake)
            strs.append(f"{snowflake}: `{snowflake_time.strftime('%A %B %d, %Y at %X UTC')}` \N{EM DASH} "
                        f"{td_format(snowflake_time - datetime.utcnow(), append_str=True)}")
        await ctx.send_interactive(pagify("\n".join(strs)))
