import asyncio
import unicodedata
from datetime import datetime

from textwrap import dedent
from inspect import getsource

import discord
from discord.ext import commands
from redbot.core import checks

from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import warning, pagify, info
from redbot.core.i18n import CogI18n

from cog_shared.odinair_libs import td_format, ConfirmMenu

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

    @commands.command(hidden=True)
    @checks.is_owner()
    async def updatered(self, ctx: RedContext, dev: bool = False, audio: bool = False, mongo: bool = False):
        """Update Red to the latest version

        If `dev` is True, then the latest version from GitHub will be used,
        with any possibly breaking changes included. Otherwise,
        Red will be updated to the latest PyPI release.
        """
        disclaimer = _(
            "**This command has not been extensively tested, and as such may have the potential to break "
            "your Red install** (regardless of how unlikely it may be.)\n\nAll responsibility for any broken "
            "installs beyond this point is passed onto the bot owner.\nIf you'd prefer to play it safe, "
            "please cancel this operation and perform an update manually, either through the Red launcher, "
            "or by manually running pip.\n\n"
            "**Please confirm that you wish to continue by clicking \N{WHITE HEAVY CHECK MARK} or \N{CROSS MARK}.**"
        )

        if not await ConfirmMenu(ctx, message=warning(disclaimer)):
            await ctx.send(info("Update cancelled."))
            return

        import sys
        interpreter = sys.executable

        # The following is mostly ripped from the Red launcher update function
        eggs = []
        if audio:
            eggs.append("audio")
        if mongo:
            eggs.append("mongo")

        if dev:
            package = "git+https://github.com/Cog-Creators/Red-DiscordBot@V3/develop"
            if eggs:
                package += "#egg=Red-DiscordBot[{}]".format(", ".join(eggs))
        else:
            package = "Red-DiscordBot"
            if eggs:
                package += "[{}]".format(", ".join(eggs))

        tmp = await ctx.send(info("Updating Red...\n\nThis may take a while, so go get yourself a cup of coffee, tea, "
                                  "or whatever other beverage you may prefer."))

        async with ctx.typing():
            p = await asyncio.create_subprocess_exec(interpreter, "-m", "pip", "install",
                                                     "-U", "--process-dependency-links", package,
                                                     stdin=None, loop=self.bot.loop)
            await p.wait()

        await tmp.delete()

        if p.returncode == 0:
            await ctx.send("Red has been updated. Please restart the bot for any updates to take affect.")
        else:
            await ctx.send("Something went wrong while updating. Please attempt an update manually.")

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

    @commands.group(aliases=["snowflake"], invoke_without_command=True)
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

    @snowflaketime.command(name="delta")
    async def snowflake_delta(self, ctx: RedContext, start: int, end: int):
        """Get the time difference between two snowflake IDs"""
        start, end = (discord.utils.snowflake_time(start), discord.utils.snowflake_time(end))
        now = datetime.utcnow()

        await ctx.send(
            _(
                "**Starting snowflake:** {start[0]} \N{EM DASH} `{start[1]}`\n"
                "**Ending snowflake:** {end[0]} \N{EM DASH} `{end[1]}`\n\n"
                "**Time difference:** {difference}"
            ).format(
                start=[td_format(start - now, append_str=True), start.strftime('%A %B %d, %Y at %X UTC')],
                end=[td_format(end - now, append_str=True), end.strftime('%A %B %d, %Y at %X UTC')],
                difference=td_format(end - start)
            )
        )
