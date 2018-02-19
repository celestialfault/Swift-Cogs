from asyncio import QueueEmpty, sleep
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from redbot.core import Config, checks, modlog
from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import error, warning

from starboard.classes.exceptions import *
from starboard.classes.guildstarboard import GuildStarboard
from starboard.classes.star import Star
from starboard.classes.starboardbase import StarboardBase
from starboard.checks import allowed_starboard, guild_has_starboard

from odinair_libs.checks import cogs_loaded
from odinair_libs.formatting import tick
from odinair_libs.menus import confirm


class Starboard(StarboardBase):
    """The poor man's channel pins"""

    def __init__(self, bot: Red, config: Config):
        self.bot = bot
        self.config = config
        self._main_task = self.bot.loop.create_task(self._main_timer())
        self._case_task = self.bot.loop.create_task(self._register_cases())

    @staticmethod
    async def _register_cases():
        try:
            await modlog.register_casetypes([
                {
                    "name": "starboardblock",
                    "default_setting": False,
                    "image": "\N{NO ENTRY SIGN}",
                    "case_str": "Starboard Block"
                },
                {
                    "name": "starboardunblock",
                    "default_setting": False,
                    "image": "\N{DOVE OF PEACE}",
                    "case_str": "Starboard Unblock"
                }
            ])
        except RuntimeError:
            pass

    @commands.command()
    @commands.guild_only()
    @allowed_starboard()
    async def star(self, ctx: RedContext, message_id: int):
        """Star a message by it's ID"""
        if not await guild_has_starboard(ctx):
            return
        message = await self.starboard(ctx.guild).message_by_id(message_id, channel_id=ctx.channel.id, auto_create=True)
        if not message:
            await ctx.send("Sorry, I couldn't find that message.")
            return
        if not message.can_star:
            await ctx.send(
                warning("That message cannot be starred as it does not have any content or attachments"),
                delete_after=15)
            return
        if await self.starboard(ctx.guild).is_ignored(message.message.author):
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

    @commands.command()
    @commands.guild_only()
    @allowed_starboard()
    async def unstar(self, ctx: RedContext, message_id: int):
        """Unstar a message by it's ID"""
        if not await guild_has_starboard(ctx):
            return
        message = await self.starboard(ctx.guild).message_by_id(message_id, channel_id=ctx.channel.id, auto_create=True)
        if not message:
            await ctx.send("Sorry, but I couldn't find that message \N{WORRIED FACE}")
            return
        if not message.exists:
            await ctx.send(warning("That message hasn't been starred by anyone yet"))
            return
        if await self.starboard(ctx.guild).is_ignored(message.message.author):
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
    async def stars(self, ctx: RedContext):
        """Manage starboard messages"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @stars.command(name="hide")
    async def stars_hide(self, ctx: RedContext, message_id: int):
        """Hide a message from the starboard"""
        star = await self.starboard(ctx.guild).message_by_id(message_id)
        if not star:
            await ctx.send(error("That message hasn't been starred"))
            return
        if not await star.hide():
            await ctx.send(error("That message is already hidden"))
        else:
            await ctx.send(tick("The message sent by **{0.message.author!s}** is now hidden.".format(star)))

    @stars.command(name="unhide")
    async def stars_unhide(self, ctx: RedContext, message_id: int):
        """Unhide a previously hidden message"""
        star = await self.starboard(ctx.guild).message_by_id(message_id)
        if not star:
            await ctx.send(error("That message hasn't been starred"))
            return
        if not await star.unhide():
            await ctx.send(error("That message hasn't been hidden"))
        else:
            await ctx.send(tick("The message sent by **{0.message.author!s}** is no longer hidden.".format(star)))

    @stars.command(name="block", aliases=["blacklist", "ban"])
    async def stars_block(self, ctx: RedContext, member: discord.Member, *, reason: str = None):
        """Block the passed user from using this guild's starboard

        For ignoring a channel from the starboard, see `[p]starboard ignore`
        """
        if await self.bot.is_owner(ctx.author)\
                or (ctx.guild.owner == ctx.author and not await self.bot.is_owner(member)):
            # allow the bot owner to block anyone, and allow guild owners to block admins, but
            # not the bot owner
            pass
        elif any([await self.bot.is_admin(member),
                  await self.bot.is_mod(member) and not await self.bot.is_admin(ctx.author),
                  await self.bot.is_owner(member), member.id == ctx.guild.owner.id]):
            # don't allow mods to block other mods or admins, but allow admins to block mods
            await ctx.send(error("You aren't allowed to block that member"))
            return
        starboard = self.starboard(ctx.guild)
        if await starboard.block_member(member):
            await ctx.tick()
            try:
                await modlog.create_case(ctx.guild, ctx.message.created_at, "starboardblock",
                                         member, ctx.author, reason, until=None, channel=None)
            except RuntimeError:
                pass
        else:
            await ctx.send(error("That user is already blocked from using this guild's starboard"))

    @stars.command(name="unblock", aliases=["unblacklist", "unban"])
    async def stars_unblock(self, ctx: RedContext, member: discord.Member, *, reason: str = None):
        """Unblocks the passed user from using this guild's starboard

        For unignoring a channel from the starboard, see `[p]starboard unignore`
        """
        starboard = self.starboard(ctx.guild)
        if await starboard.unblock_member(member):
            await ctx.tick()
            try:
                await modlog.create_case(ctx.guild, ctx.message.created_at, "starboardunblock",
                                         member, ctx.author, reason, until=None, channel=None)
            except RuntimeError:
                pass
        else:
            await ctx.send(error("That user isn't blocked from using this guild's starboard"))

    @stars.command(name="update", hidden=True)
    async def stars_update(self, ctx: RedContext, message_id: int):
        """Force update a starboard message"""
        starboard = self.starboard(ctx.guild)  # type: GuildStarboard
        star = await starboard.message_by_id(message_id)  # type: Star
        if star is None:
            await ctx.send(warning("I couldn't find that message - has it been starred before?"))
            return
        # force a recache of the message
        await starboard.remove_from_cache(star.message)
        star = await starboard.message_by_id(message_id)  # type: Star
        star.in_queue = True
        await ctx.send(tick("The message sent by **{0.message.author!s}** has been queued to be updated".format(star)))

    @commands.group(name="starboard")
    @checks.admin_or_permissions(manage_channels=True)
    async def cmd_starboard(self, ctx: RedContext):
        """Manage the guild's starboard"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @cmd_starboard.command(name="channel")
    async def starboard_channel(self, ctx: RedContext, channel: discord.TextChannel=None):
        """Set or clear the guild's starboard channel"""
        if channel and channel.guild.id != ctx.guild.id:
            await ctx.send(error("That channel isn't in this guild"))
            return
        await self.starboard(ctx.guild).channel(channel=channel)
        if channel is None:
            await ctx.send(tick("Cleared the current starboard channel"))
        else:
            await ctx.send(tick("Set the starboard channel to {0.mention}".format(channel)))

    @cmd_starboard.command(name="stars", aliases=["minstars"])
    async def starboard_minstars(self, ctx: RedContext, stars: int):
        """Set the amount of stars required for a message to be sent to this guild's starboard"""
        if stars < 1:
            await ctx.send(error("The amount of stars must be a non-zero number"))
            return
        if stars > len(ctx.guild.members):
            await ctx.send(error("There aren't enough members in this server to reach that amount of stars"))
            return
        await self.starboard(ctx.guild).min_stars(stars)
        await ctx.tick()

    @cmd_starboard.command(name="ignore")
    async def starboard_ignore(self, ctx: RedContext, *, channel: discord.TextChannel):
        """Ignore a channel, preventing any stars from occurring in it

        For ignoring a member from the starboard, see `[p]stars block`
        """
        if await self.starboard(ctx.guild).ignore_channel(channel):
            await ctx.tick()
        else:
            await ctx.send(error("That channel is already ignored from this guild's starboard"))

    @cmd_starboard.command(name="unignore")
    async def starboard_unignore(self, ctx: RedContext, *, channel: discord.TextChannel):
        """Unignore a channel, allowing stars to occur

        For unignoring a member from the starboard, see `[p]stars unblock`
        """
        if await self.starboard(ctx.guild).unignore_channel(channel):
            await ctx.tick()
        else:
            await ctx.send(error("That channel isn't ignored from this guild's starboard"))

    @cmd_starboard.command(name="clearcache", hidden=True)
    async def starboard_clearcache(self, ctx: RedContext, max_duration: int = 30 * 60):
        """Prune the internal message cache

        Any items that are in the queue to be updated and also qualify to be pruned are updated before being un-cached.

        Any messages that are cleared from the cache will need to be re-cached
        if any actions are done on them, such as a member starring or unstarring,
        or the message being hidden from the starboard.

        `max_duration` may be set to 0 to clear *all* items from the internal cache.
        """
        items_to_remove = await self.starboard(ctx.guild).purge_cache(seconds_since_update=max_duration, dry_run=True)
        if items_to_remove == 0:
            await ctx.send(warning("Found no items to remove from the cache."))
            return
        if await confirm(ctx, "Are you sure you want to remove {} item(s) from the cache?".format(items_to_remove),
                         colour=discord.Colour.gold()):
            purged = await self.starboard(ctx.guild).purge_cache(seconds_since_update=max_duration)
            await ctx.send(tick("Cleared {} item(s) from the cache".format(purged)))
        else:
            await ctx.send("Okay then.", delete_after=20)

    @cmd_starboard.command(name="requirerole")
    @cogs_loaded("RequireRole")
    async def starboard_respect_requirerole(self, ctx: RedContext):
        """Toggle whether or not the starboard respects your RequireRole settings"""
        starboard = self.starboard(ctx.guild)
        current = await starboard.config.respect_requirerole()
        current = not current
        await starboard.config.respect_requirerole.set(current)
        await ctx.send("{} respecting RequireRole settings.".format("Now" if current else "No longer"))

    async def on_raw_reaction_add(self, emoji: discord.PartialEmoji, message_id: int, channel_id: int, user_id: int):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return
        # check that the channel is in a guild
        if isinstance(channel, discord.abc.PrivateChannel) or not hasattr(channel, "guild"):
            return
        guild = channel.guild
        starboard = self.starboard(guild)
        # check the reaction is a star emoji
        if not emoji.is_unicode_emoji() or str(emoji) != "\N{WHITE MEDIUM STAR}":
            return

        member = guild.get_member(user_id)
        # check if the member or channel is ignored
        if await starboard.is_ignored(member) or await starboard.is_ignored(channel):
            return

        message = await self.starboard(guild).message_by_id(message_id=message_id,
                                                            channel_id=channel_id,
                                                            auto_create=True)
        if message.has_starred(member):
            return
        try:
            await message.add_star(member)
        except StarboardException:
            pass

    async def on_raw_reaction_remove(self, emoji: discord.PartialEmoji, message_id: int, channel_id: int, user_id: int):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return
        # check that the channel is in a guild
        if isinstance(channel, discord.abc.PrivateChannel) or not hasattr(channel, "guild"):
            return
        guild = channel.guild
        starboard = self.starboard(guild)
        # check the reaction is a star emoji
        if emoji.is_custom_emoji() or str(emoji) != "\N{WHITE MEDIUM STAR}":
            return

        member = guild.get_member(user_id)
        if await starboard.is_ignored(member) or await starboard.is_ignored(channel):
            return

        message = await self.starboard(guild).message_by_id(message_id=message_id,
                                                            channel_id=channel_id)
        if not message.has_starred(member):
            return
        try:
            await message.remove_star(member)
        except StarboardException:
            pass

    def __unload(self):
        self._main_task.cancel()
        self._case_task.cancel()
        # Ensure that all remaining items in the queue are properly handled
        self.bot.loop.create_task(self._empty_starboard_queue())

    async def _main_timer(self):
        time_since = {}
        while self == self.bot.get_cog("Starboard"):
            # Update starboard messages - always runs every loop
            for starboard in self.guild_starboard_cache():
                starboard = self.guild_starboard_cache()[starboard]
                try:
                    await starboard.handle_queue()
                except QueueEmpty:
                    pass

            # Housekeeping - runs every hour
            housekeep_check = time_since.get("housekeep", datetime.fromtimestamp(0)) + timedelta(hours=1)
            if housekeep_check < datetime.utcnow():
                self.bot.loop.create_task(self._handle_housekeeping())
                time_since["housekeep"] = datetime.utcnow()

            # Cache cleanup - runs every 15 minutes
            cleanup_check = time_since.get("cache_clean", datetime.fromtimestamp(0)) + timedelta(minutes=15)
            if cleanup_check < datetime.utcnow():
                self.bot.loop.create_task(self._cache_cleanup())
                time_since["cache_clean"] = datetime.utcnow()

            # Sleep for 5 seconds
            await sleep(5)

    async def _cache_cleanup(self):
        for starboard in self.guild_starboard_cache():
            starboard = self.guild_starboard_cache()[starboard]
            await starboard.purge_cache()

    async def _handle_housekeeping(self):
        for starboard in self.guild_starboard_cache():
            starboard = self.guild_starboard_cache()[starboard]
            await starboard.housekeep()

    async def _empty_starboard_queue(self):
        for starboard in self.guild_starboard_cache():
            starboard = self.guild_starboard_cache()[starboard]
            try:
                await starboard.handle_queue()
            except QueueEmpty:
                continue
