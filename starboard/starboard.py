from typing import Union

import discord
from discord.ext import commands
from redbot.core import Config, checks
from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import error, warning

from .classes.exceptions import *
from .checks import allowed_starboard
from .classes.starboardbase import StarboardBase


class Starboard(StarboardBase):
    """
    The poor man's channel pins
    """

    def __init__(self, bot: Red, config: Config):
        self.bot = bot
        self.config = config

    @commands.command(name="star")
    @commands.guild_only()
    @allowed_starboard()
    async def _star(self, ctx: RedContext, message_id: int):
        """
        Star a message in the current channel by it's ID
        """
        try:
            message = await ctx.get_message(message_id)
        except discord.NotFound:
            await ctx.send(error("That message doesn't exist in this channel"))
        except discord.Forbidden:
            await ctx.send(error("I'm not allowed to retrieve message logs"))
        except discord.HTTPException:
            await ctx.send(error("An error occurred while attempting to retrieve that message"))
        else:
            message = await self.message(message, auto_create=True)
            try:
                await message.add(ctx.author)
            except StarException:
                await ctx.send(
                    warning("You've already starred that message\n\n(you can use `{}unstar` to remove your star)"
                            .format(ctx.prefix)),
                    delete_after=15)
            except BlockedAuthorException:
                await ctx.send(error("The author of that message has been blocked from using this guild's starboard"),
                               delete_after=15)
            except BlockedException:
                await ctx.send(error("You have been blocked from using this guild's starboard"),
                               delete_after=15)
            else:
                await ctx.tick()

    @commands.command(name="unstar")
    @commands.guild_only()
    @allowed_starboard()
    async def _unstar(self, ctx: RedContext, message_id: int):
        """
        Unstars a message in the current channel by it's ID
        """
        try:
            message = await ctx.get_message(message_id)
        except discord.NotFound:
            await ctx.send(error("That message doesn't exist in this channel"))
        except discord.Forbidden:
            await ctx.send(error("I'm not allowed to retrieve message logs"))
        except discord.HTTPException:
            await ctx.send(error("An error occurred while attempting to retrieve that message"))
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
            except BlockedAuthorException:
                await ctx.send(error("The author of that message has been blocked from using this guild's starboard"),
                               delete_after=15)
            except BlockedException:
                await ctx.send(error("You have been blocked from using this guild's starboard"),
                               delete_after=15)
            else:
                await ctx.tick()

    @commands.group(name="stars")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def _stars(self, ctx: RedContext):
        """
        Manage starboard messages
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @_stars.command(name="hide")
    async def _stars_hide(self, ctx: RedContext, message_id: int):
        star = await self.starboard(ctx.guild).message_by_id(message_id)
        if not star:
            await ctx.send(error("That message hasn't been starred"))
            return
        try:
            await star.hide()
        except HideException:
            await ctx.send(error("That message is already hidden"))
        else:
            await ctx.tick()

    @_stars.command(name="unhide")
    async def _stars_unhide(self, ctx: RedContext, message_id: int):
        star = await self.starboard(ctx.guild).message_by_id(message_id)
        if not star:
            await ctx.send(error("That message hasn't been starred"))
            return
        try:
            await star.unhide()
        except HideException:
            await ctx.send(error("That message hasn't been hidden"))
        else:
            await ctx.tick()

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

    @_starboard.command(name="stars", aliases=["minstars"])
    async def _starboard_minstars(self, ctx: RedContext, stars: int):
        """
        Set the amount of stars required for a message to be sent to this guild's starboard
        """
        if stars < 1:
            await ctx.send(error("The amount of stars must be a non-zero number"))
            return
        if stars > len(ctx.guild.members):
            await ctx.send(error("There aren't enough members in this server to reach that amount of stars"))
            return
        await self.starboard(ctx.guild).minstars(stars)
        await ctx.tick()

    @_starboard.command(name="block", aliases=["blacklist", "ban"])
    async def _starboard_block(self, ctx: RedContext, *, member: discord.Member):
        """
        Block the passed user from using this guild's starboard
        """
        if await self.bot.is_owner(member):  # prevent blocking of the bot owner
            await ctx.send(error("You aren't allowed to block that member"))
            return
        elif ctx.guild.owner.id == ctx.author.id:  # allow guild owners to block admins and mods
            pass
        elif await self.bot.is_admin(member):  # prevent blocking of admins
            await ctx.send(error("You aren't allowed to block that member"))
            return
        elif await self.bot.is_mod(member) and not await self.bot.is_admin(ctx.author):
            # prevent mods blocking other moderators, but allow admins to block mods
            await ctx.send(error("You aren't allowed to block that member"))
            return
        starboard = self.starboard(ctx.guild)
        if await starboard.block(member):
            await ctx.tick()
        else:
            await ctx.send(error("That user is already blocked from using this guild's starboard"))

    @_starboard.command(name="unblock", aliases=["unblacklist", "unban"])
    async def _starboard_unblock(self, ctx: RedContext, *, member: discord.Member):
        """
        Unblocks the passed user from using this guild's starboard
        """
        starboard = self.starboard(ctx.guild)
        if await starboard.unblock(member):
            await ctx.tick()
        else:
            await ctx.send(error("That user isn't blocked from using this guild's starboard"))

    async def on_reaction_add(self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]):
        if not str(reaction.emoji) == "⭐" or not isinstance(user, discord.Member):
            return
        message = reaction.message
        if await self.starboard(message.guild).is_blocked(user):
            return
        message = await self.message(message, auto_create=True)
        try:
            await message.add(user)
        except StarException:
            pass
        except BlockedException:
            pass

    async def on_reaction_remove(self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]):
        if not str(reaction.emoji) == "⭐" or not isinstance(user, discord.Member):
            return
        message = reaction.message
        if await self.starboard(message.guild).is_blocked(user):
            return
        message = await self.message(message)
        if not message or not message.user_count:
            return
        try:
            await message.remove(user)
        except StarException:
            pass
        except BlockedException:
            pass
