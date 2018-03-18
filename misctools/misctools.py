from datetime import datetime

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import warning, pagify, box
from redbot.core.i18n import CogI18n

import unicodedata

from odinair_libs.formatting import td_format, get_source

_ = CogI18n("MiscTools", __file__)


class MiscTools:
    """Various quick & dirty utilities
    Mostly useful when making cogs, and/or for advanced server administration use.
    """

    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = "0.1.0"

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

    @commands.command(hidden=True)
    async def test_menu(self, ctx: RedContext):
        """A very simple example command that uses ReactMenu

        This isn't a proper command (unless you like being asked for a number between one and three),
        and is meant as an example for my library cog's `ReactMenu` class.

        The aforementioned library cog can be found as `odinair_libs`
        in my cog repository: https://github.com/notodinair/Red-Cogs/tree/v3
        """
        from odinair_libs.menus import ReactMenu, PostMenuAction
        # This command is meant as a fairly basic example usage of ReactMenu,
        # with comments to explain most features used.
        # There's a *lot* more functionality that isn't covered here.
        # If you'd like to use this in an external cog, feel free to adapt this to your own use case.
        # Implementing i18n support in this example is left as an exercise for the reader.

        # This is a dict of actions in the form of { action: emoji }
        # Note that the default value (passed as the `default` keyword argument when creating a ReactMenu)
        # does not need to be in the actions dict
        # Accepted emoji types are unicode emojis (such as below), or `discord.Emoji` items
        # The action is returned as an attribute named `action` in a MenuResult class, in the form of either
        # a key in the actions dict you passed when creating the ReactMenu, or the value of `default`
        actions = {
            "One": "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}",
            "Two": "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}",
            "Three": "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}"
        }
        menu = ReactMenu(ctx=ctx, actions=actions, content="Choose a number", post_action=PostMenuAction.DELETE,
                         default="Default")
        async with menu as result:
            # Send the result in chat
            await ctx.send(f"Result:\n{box(repr(result), lang='py')}")
