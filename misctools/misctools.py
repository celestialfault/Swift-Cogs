import re
from datetime import datetime

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import warning, pagify

import unicodedata

from odinair_libs.formatting import td_format

import inspect


class MiscTools:
    """Various quick & dirty utilities
    Mostly useful when making cogs, and/or for advanced server administration use.
    """

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    async def rtfs(self, ctx: RedContext, *, command_name: str):
        """Get the source for a command or subcommand"""
        command = self.bot.get_command(command_name)
        if command is None:
            await ctx.send(warning("That command doesn't exist"))
            return
        lines, _ = inspect.getsourcelines(command.callback.__code__)
        source = "".join(lines)
        # replace tabs with 4 spaces
        re.compile(r"\t", re.MULTILINE).sub("\N{SPACE}" * 4, source)
        regex = re.compile(r"^( +)")
        indent = regex.search(source)
        if indent:
            # determine indentation from the first line, which is usually the command decorator
            spaces = indent.group(0)
            regex = re.compile(r"^({})".format(" " * len(spaces)), re.MULTILINE)
            source = regex.sub("", source)
        await ctx.send_interactive(pagify(source, shorten_by=10, delims=["\n"]), box_lang="py")

    @commands.command()
    async def charinfo(self, ctx: RedContext, *, characters: str):
        """Get the unicode name for characters"""
        if len(characters) > 25:
            await ctx.send(warning("You can only pass up 25 characters at once"))
            return

        def to_string(c):
            return "{0} \N{EM DASH} {1}".format(c, unicodedata.name(c, "Name not found"))

        await ctx.send("\n".join(map(to_string, characters)))

    @commands.command(name="pingtime", aliases=["pingt"])
    async def ping(self, ctx: RedContext):
        """Get the time it takes the bot to respond to a command

        This is by no means fully accurate, and should be treated similarly to rough estimate

        Time to command execution means how long it took for the bot to receive the command message
        and execute this command

        Usually you'll only care about the typing indicator, since it stands for how long it took
        for the bot to send an API request to Discord and start 'typing'.
        """
        now = datetime.utcnow()
        to_execution = td_format(now - ctx.message.created_at, milliseconds=True, short_format=True)
        await ctx.trigger_typing()
        time_to_typing = td_format(datetime.utcnow() - now, milliseconds=True, short_format=True)
        full_round_trip = td_format(datetime.utcnow() - ctx.message.created_at, milliseconds=True, short_format=True)
        await ctx.send(content="\N{TABLE TENNIS PADDLE AND BALL} Pong!"
                                "\nTime to command execution: {execution}"
                                "\nTyping indicator: {typing}"
                                "\n\nFull round trip: {rt}".format(execution=to_execution, typing=time_to_typing,
                                                                   rt=full_round_trip))

    @commands.command()
    async def snowflake(self, ctx: RedContext, snowflake: int):
        """Get the time a snowflake was created at"""
        snowflake_time = discord.utils.snowflake_time(snowflake)
        await ctx.send("{0}: `{1}` ({2} ago)".format(snowflake, snowflake_time,
                                                     td_format(datetime.utcnow() - snowflake_time)))

    @commands.command(hidden=True)
    async def test_menu(self, ctx: RedContext):
        """A very simple example of how to use react_menu

        This isn't a proper command (unless you like being asked for a number between one and three),
        and is meant as an example for my library cog's `react_menu` function.
        You can retrieve the source for this with `[p]rtfs test_menu`.

        The aforementioned library cog can be found as `odinair_libs`
        in my cog repository: https://github.com/notodinair/Red-Cogs/tree/v3
        """
        from odinair_libs.menus import react_menu, PostMenuAction
        from odinair_libs.formatting import attempt_emoji
        # This command is meant as a fairly basic example usage of react_menu,
        # with comments to explain most features used.
        # There's a *lot* more functionality that isn't covered here.
        # If you'd like to use this in an external cog, feel free to adapt this to your own use case
        # For an example on pagination, see the `logset info` command in my Logs cog
        # For more information on the following fields used, please check the docs for the react_menu function

        # The following function attempts to retrieve a guild emoji by ID and / or name, with a fallback unicode emoji
        # The emoji used below: https://cdn.discordapp.com/emojis/379046291386400769.png
        # Example usages can include guild-configurable emojis for actions
        null_tick = attempt_emoji(
            # an emoji id to get, this can be useful for cogs designed for a specific bot
            # otherwise, if guilds have their own version of the same emoji,
            # emoji_name may be better suited
            emoji_id=379046291386400769,
            # a case sensitive emoji name to try to resolve
            # this is ignored if emoji_id finds an emoji
            emoji_name="NullTick",
            # fallback is used if neither emoji_id nor  emoji_name finds an emoji
            fallback="\N{MEDIUM WHITE SQUARE}")

        # This is a dict of actions in the form of { (action: Any): (emoji: discord.Emoji or str) }
        actions = {
            # Available emoji types are plain unicode emojis (such as below), or `discord.Emoji` items
            # The action is what's returned back to you in `<MenuResult>.action`
            "One": "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}",
            "Two": "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}",
            "Three": "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}",
            "Null Tick": null_tick
        }
        # Content is the text that appears on the message that the react menu is enabled on
        # The following fields are also available:
        #  embed: discord.Embed - a embed to use, this can be combined with `content`
        #  message: discord.Message - a message that's already been sent, if this isn't None then `content` and `embed`
        #                             are ignored and the message given is used instead
        # The returned action taken can be accessed with `.action`, and is in the form of either an item in `actions`,
        # or the value of `default`
        # In the event that you can't import react_menu, you can also access it with `libs.menus.react_menu`,
        # where `libs` is the loaded OdinairLibs cog class
        result = await react_menu(ctx, actions, content="Choose a number", post_action=PostMenuAction.DELETE,
                                  default="Default")
        # Echo back the response the user chose
        await ctx.send("You chose: {0.action}".format(result))
