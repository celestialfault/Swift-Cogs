from typing import Union

import discord
from discord.ext import commands
from redbot.core import Config, checks
from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import info, error, warning, box

from .classes.exceptions import *
from .classes.starboardbase import StarboardBase


class Starboard(StarboardBase):
    def __init__(self, bot: Red, config: Config):
        super().__init__()
        self.bot = bot
        self.config = config

    @commands.command(name="star")
    @commands.guild_only()
    async def _star(self, ctx: RedContext, message_id: int):
        """
        Star a entry by it's ID
        """
        try:
            message = await ctx.get_message(message_id)
        except discord.NotFound:
            await ctx.send(error("That message doesn't exist in this channel"))
        except discord.Forbidden:
            await ctx.send(error("I'm not allowed to retrieve message logs"))
        except discord.HTTPException:
            await ctx.send(error("An error occured while attempting to retrieve that message"))
        else:
            message = await self.message(message, auto_create=True)
            try:
                await message.add(ctx.author)
            except StarException:
                await ctx.send(
                    warning("You've already starred that message\n\n(you can use `{}unstar` to remove your star)"
                            .format(ctx.prefix)),
                    delete_after=15)
            else:
                await ctx.tick()

    @commands.command(name="unstar")
    @commands.guild_only()
    async def _unstar(self, ctx: RedContext, message_id: int):
        """
        Unstars a message by it's ID
        """
        try:
            message = await ctx.get_message(message_id)
        except discord.NotFound:
            await ctx.send(error("That message doesn't exist in this channel"))
        except discord.Forbidden:
            await ctx.send(error("I'm not allowed to retrieve message logs"))
        except discord.HTTPException:
            await ctx.send(error("An error occured while attempting to retrieve that message"))
        else:
            message = await self.message(message)
            if not message.entry_exists:
                await ctx.send(warning("That message hasn't been starred yet"))
                return
            try:
                await message.remove(ctx.author)
            except StarException:
                await ctx.send(
                    warning("You haven't starred that message\n\n(you can use `{}star` to star it)"
                            .format(ctx.prefix)),
                    delete_after=15)
            else:
                await ctx.tick()

    # TODO: Implement message hiding
    @commands.group(name="stars", hidden=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def _stars(self, ctx: RedContext):
        """
        Manage starboard messages
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @_stars.command(name="hide")
    async def _stars_hide(self, ctx: RedContext):
        raise NotImplementedError

    @_stars.command(name="unhide")
    async def _stars_unhide(self, ctx: RedContext):
        raise NotImplementedError

    @commands.group(name="starboard")
    @checks.admin_or_permissions(manage_channels=True)
    async def _starboard(self, ctx: RedContext):
        """
        Manage the guild's starboard
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @_starboard.command(name="channel")
    async def _starboard_channel(self, ctx: RedContext, channel: discord.TextChannel=None):
        if not channel:
            await self.starboard(ctx.guild).channel(clear=True)
        else:
            await self.starboard(ctx.guild).channel(channel=channel)
        await ctx.tick()

    @_starboard.group(name="debug")
    @checks.is_owner()
    async def _starboard_debug(self, ctx: RedContext):
        """
        Starboard debug tools
        """
        if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == "debug":
            await ctx.send_help()

    @_starboard_debug.command(name="message")
    async def _debug_message(self, ctx: RedContext, message_id: int):
        starboard = self.starboard(ctx.guild)
        data = await starboard.message_by_id(message_id)
        await ctx.send(box(text=data, lang="python"))

    async def on_reaction_add(self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]):
        if not str(reaction.emoji) == "⭐" or not isinstance(user, discord.Member):
            return
        message = reaction.message
        message = await self.message(message, auto_create=True)
        try:
            await message.add(user)
        except StarException:
            pass

    async def on_reaction_remove(self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]):
        if not str(reaction.emoji) == "⭐" or not isinstance(user, discord.Member):
            return
        message = reaction.message
        message = await self.message(message)
        if not message or not message.user_count:
            return
        try:
            await message.remove(user)
        except StarException:
            pass
