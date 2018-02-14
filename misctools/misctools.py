from datetime import datetime

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import warning, pagify

import unicodedata

from odinair_libs.formatting import td_format, get_source


class MiscTools:
    """Various quick & dirty utilities
    Mostly useful when making cogs, and/or for advanced server administration use.
    """

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    async def rtfs(self, ctx: RedContext, *, command_name: str):
        """Get the source for a command or sub command"""
        command = self.bot.get_command(command_name)
        if command is None:
            await ctx.send(warning("That command doesn't exist"))
            return
        await ctx.send_interactive(pagify(get_source(command.callback), shorten_by=10), box_lang="py")

    @commands.command()
    async def charinfo(self, ctx: RedContext, *, characters: str):
        """Get the unicode name for characters"""
        if len(characters) > 25:
            await ctx.send(warning("You can only pass up 25 characters at once"))
            return
        await ctx.send("\n".join(map(lambda c: "{0} \N{EM DASH} {1}".format(c, unicodedata.name(c, "Name not found")),
                                     characters)))

    @commands.command(name="pingtime", aliases=["pingt"])
    async def ping(self, ctx: RedContext):
        """Get the time it takes the bot to respond to a command

        This is by no means fully accurate, and should be treated similarly to rough estimate

        Time to command execution means how long it took for the bot to receive the command message
        and execute the command
        """
        to_execution = td_format(datetime.utcnow() - ctx.message.created_at, milliseconds=True, short_format=True)
        now = datetime.utcnow()
        await ctx.trigger_typing()
        time_to_typing = td_format(datetime.utcnow() - now, milliseconds=True, short_format=True)
        full_round_trip = td_format(datetime.utcnow() - ctx.message.created_at, milliseconds=True, short_format=True)
        await ctx.send(content="\N{TABLE TENNIS PADDLE AND BALL} Pong!"
                                "\nTime to command execution: {execution}"
                                "\nTyping indicator: {typing}"
                                "\n\nFull round trip: {rt}".format(execution=to_execution, typing=time_to_typing,
                                                                   rt=full_round_trip))

    @commands.command()
    async def snowflake(self, ctx: RedContext, *snowflakes: int):
        """Get the time that one or more snowflake IDs were created at"""
        if not snowflakes:
            await ctx.send_help()
            return
        strs = []
        for snowflake in snowflakes:
            snowflake_time = discord.utils.snowflake_time(snowflake)
            strs.append("{0}: `{1}` ({2} ago)".format(snowflake, snowflake_time,
                                                      td_format(datetime.utcnow() - snowflake_time)))
        await ctx.send_interactive(pagify("\n".join(strs)))

    @commands.command(hidden=True)
    async def test_menu(self, ctx: RedContext):
        """A very simple example command that uses ReactMenu

        This isn't a proper command (unless you like being asked for a number between one and three),
        and is meant as an example for my library cog's `ReactMenu` function.
        You can retrieve the source for this with `[p]rtfs test_menu`.

        The aforementioned library cog can be found as `odinair_libs`
        in my cog repository: https://github.com/notodinair/Red-Cogs/tree/v3
        """
        from odinair_libs.menus import PostMenuAction, ReactMenu
        from odinair_libs.formatting import attempt_emoji
        # This command is meant as a fairly basic example usage of ReactMenu,
        # with comments to explain most features used.
        # There's a *lot* more functionality that isn't covered here.
        # If you'd like to use this in an external cog, feel free to adapt this to your own use case
        # For an example on pagination, see the `logset info` command in my Logs cog
        # For more information on the following fields used, please check the docs for the ReactMenu function

        # The following function attempts to retrieve a guild emoji by ID and / or name, with a fallback unicode emoji
        # The emoji used below: https://cdn.discordapp.com/emojis/379046291386400769.png
        # Example usages can include guild-configurable emojis for actions
        null_tick = attempt_emoji(
            # an emoji id to get, this can be useful for cogs designed for a specific bot
            # otherwise, if guilds have their own version of the same emoji,
            # emoji_name may be better suited
            emoji_id=379046291386400769,
            # a case sensitive emoji name to try to resolve
            # this is ignored if an exact emoji is found from the emoji_id field
            emoji_name="NullTick",
            # fallback is used if neither emoji_id nor emoji_name finds an emoji
            fallback="")

        # This is a dict of actions in the form of { (action: Any): (emoji: discord.Emoji or str) }
        actions = {
            # Available emoji types are plain unicode emojis (such as below), or `discord.Emoji` items
            # The action is what's returned back to you in `<MenuResult>.action`
            "One": "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}",
            "Two": "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}",
            "Three": "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}"
        }
        if null_tick != "":
            actions["Null Tick"] = null_tick
        # Content is the text that appears on the message that the react menu is enabled on
        # The following fields are also available:
        #  embed: discord.Embed - a embed to use, this can be combined with `content`
        #  message: discord.Message - a message that's already been sent, if this isn't None then `content` and `embed`
        #                             are ignored and the message given is used instead
        # The returned action taken can be accessed with `.action`, and is in the form of either an item in `actions`,
        # or the value of `default`
        # In the event that you can't import ReactMenu, you can also access it with `libs.menus.ReactMenu`,
        # where `libs` is the loaded OdinairLibs cog class, or the return value of bot.get_cog('OdinairLibs')
        menu = ReactMenu(ctx, actions, content="Choose a number", post_action=PostMenuAction.DELETE, default="Default")
        result = await menu.prompt()
        # Echo back the response the user chose
        await ctx.send("You chose: {0.action}".format(result))
