import asyncio
from asyncio import QueueEmpty
from typing import Union

import discord
from discord.ext import commands
from redbot.core import Config, checks
from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import error, warning

from .classes.exceptions import *
from .classes.starboardbase import StarboardBase
from .checks import allowed_starboard


class Starboard(StarboardBase):
    """The poor man's channel pins"""

    def __init__(self, bot: Red, config: Config):
        self.bot = bot
        self.config = config
        self.bot.loop.create_task(self.cache_cleanup())
        self.bot.loop.create_task(self.starboard_queue())

    @commands.command(name="star")
    @commands.guild_only()
    @allowed_starboard()
    async def _star(self, ctx: RedContext, message_id: int):
        """
        Star a message in the current channel by it's ID
        """
        starboard = self.starboard(ctx.guild)
        if await starboard.channel() is None:
            await ctx.send(warning("This guild does not have a starboard channel setup"))
            return
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
            if not message.can_star:
                await ctx.send(
                    warning("That message cannot be starred as it does not have any content or attachments"),
                    delete_after=15)
                return
            if await self.starboard(ctx.guild).is_blocked(message.message.author):
                await ctx.send(error("The author of that message has been blocked from using this guild's starboard"),
                               delete_after=15)
                return
            if message.has_starred(ctx.author):
                await ctx.send(
                    warning("You've already starred that message\n\n(you can use `{}unstar` to remove your star)"
                            .format(ctx.prefix)),
                    delete_after=15)
                return
            await message.add_star(ctx.author)
            await ctx.tick()

    @commands.command(name="unstar")
    @commands.guild_only()
    @allowed_starboard()
    async def _unstar(self, ctx: RedContext, message_id: int):
        """
        Unstars a message in the current channel by it's ID
        """
        starboard = self.starboard(ctx.guild)
        if await starboard.channel() is None:
            await ctx.send(warning("This guild does not have a starboard channel setup"))
            return
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
            if not message.exists:
                await ctx.send(warning("That message hasn't been starred yet"))
                return
            if await self.starboard(ctx.guild).is_blocked(message.message.author):
                await ctx.send(error("The author of that message has been blocked from using this guild's starboard"),
                               delete_after=15)
                return
            if not message.has_starred(ctx.author):
                await ctx.send(
                    warning("You haven't starred that message\n\n(you can use `{}star` to star it)"
                            .format(ctx.prefix)),
                    delete_after=15)
                return
            await message.remove_star(ctx.author)
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
        """Hide a message from the starboard"""
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
        """Unhide a previously hidden message"""
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
        """Set or clear the guild's starboard channel"""
        if channel and channel.guild.id != ctx.guild.id:
            await ctx.send(error("That channel isn't in this guild"))
            return
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
        await self.starboard(ctx.guild).min_stars(stars)
        await ctx.tick()

    @_starboard.command(name="block", aliases=["blacklist", "ban"])
    async def _starboard_block(self, ctx: RedContext, *, member: discord.Member):
        """
        Block the passed user from using this guild's starboard
        """
        if await self.bot.is_owner(member) or member.id == ctx.guild.owner.id:
            # prevent blocking of the bot/guild owner
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
        starboard = self.starboard(message.guild)
        if await starboard.channel() is None or await self.starboard(message.guild).is_blocked(user):
            return
        message = await self.message(message, auto_create=True)
        try:
            await message.add_star(user)
        except StarException:
            pass
        except BlockedException:
            pass
        except StarboardException:
            pass

    async def on_reaction_remove(self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]):
        if not str(reaction.emoji) == "⭐" or not isinstance(user, discord.Member):
            return
        message = reaction.message
        starboard = self.starboard(message.guild)
        if await starboard.channel() is None or await self.starboard(message.guild).is_blocked(user):
            return
        message = await self.message(message)
        if not message or not message.user_count:
            return
        try:
            await message.remove_star(user)
        except StarException:
            pass
        except BlockedException:
            pass
        except StarboardException:
            pass

    # noinspection PyUnusedLocal
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not after.guild:
            return
        if self.starboard(after.guild).is_cached(after):
            # Force a re-cache of the updated message contents
            await self.starboard(after.guild).remove_from_cache(after)

    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return
        msg = await self.message(message)
        if msg and msg.exists:
            try:
                await msg.hide()
            except HideException:
                pass
        # Remove the message from the cache
        await self.starboard(message.guild).remove_from_cache(message)

    def __unload(self):
        self.bot.loop.create_task(self.empty_starboard_queue())

    async def cache_cleanup(self):
        while self == self.bot.get_cog("Starboard"):  # Purge guild Star object caches every 5 minutes
            for starboard in self.guild_starboard_cache():
                starboard = self.guild_starboard_cache()[starboard]
                await starboard.purge_cache()
            await asyncio.sleep(300)

    async def empty_starboard_queue(self):
        for starboard in self.guild_starboard_cache():
            starboard = self.guild_starboard_cache()[starboard]
            try:
                await starboard.handle_queue()
            except QueueEmpty:
                continue

    async def starboard_queue(self):
        while self == self.bot.get_cog("Starboard"):
            await self.empty_starboard_queue()
            await asyncio.sleep(3)
