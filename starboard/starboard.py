from asyncio import QueueEmpty, sleep
from typing import Sequence

import discord
from discord.ext import commands
from redbot.core import Config, checks, modlog
from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import error, warning

from starboard.classes.exceptions import StarboardException
from starboard.classes.guildstarboard import GuildStarboard
from starboard.classes.star import Star
from starboard.classes.starboardbase import StarboardBase
from starboard.checks import allowed_starboard, guild_has_starboard

from odinair_libs.checks import cogs_loaded
from odinair_libs.formatting import tick


class Starboard(StarboardBase):
    """It's almost like pinning messages, except with stars"""

    def __init__(self, bot: Red, config: Config):
        self.bot = bot
        self.config = config
        self._tasks = [
            self.bot.loop.create_task(self._task_cache_cleanup()),
            self.bot.loop.create_task(self._task_message_update()),
            self.bot.loop.create_task(self._register_cases())
        ]

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
        message: Star = await self.starboard(ctx.guild).message(message_id=message_id, channel=ctx.channel,
                                                                auto_create=True)
        if not message:
            await ctx.send("Sorry, I couldn't find that message.")
            return
        if not message.is_message_valid:
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
                warning(f"You've already starred that message\n\n"
                        f"(you can use `{ctx.prefix}unstar` to remove your star)"),
                delete_after=15)
            return
        try:
            await message.add_star(ctx.author)
        except StarboardException as e:
            await ctx.send(warning(f"Failed to add star \N{EM DASH} `{e!s}`"))
        else:
            await ctx.tick()

    @commands.command()
    @commands.guild_only()
    @allowed_starboard()
    async def unstar(self, ctx: RedContext, message_id: int):
        """Unstar a message by it's ID"""
        if not await guild_has_starboard(ctx):
            return
        message = await self.starboard(ctx.guild).message(message_id=message_id)
        if not message:
            await ctx.send("Sorry, I couldn't find that message.")
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
        try:
            await message.remove_star(ctx.author)
        except StarboardException:
            await ctx.send(warning("Failed to remove star"))
        else:
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
        star = await self.starboard(ctx.guild).message(message_id=message_id)
        if not star:
            await ctx.send(error("That message either hasn't been starred, or it doesn't exist"))
            return
        if not await star.hide():
            await ctx.send(error("That message is already hidden"))
        else:
            await ctx.send(tick("The message sent by **{0.message.author!s}** is now hidden.".format(star)))

    @stars.command(name="unhide")
    async def stars_unhide(self, ctx: RedContext, message_id: int):
        """Unhide a previously hidden message"""
        star = await self.starboard(ctx.guild).message(message_id=message_id)
        if not star:
            await ctx.send(error("That message either hasn't been starred, or it doesn't exist"))
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
        starboard: GuildStarboard = self.starboard(ctx.guild)
        star: Star = await starboard.message(message_id=message_id)
        if star is None:
            await ctx.send(warning("I couldn't find a message with that ID - has the message been deleted?"))
            return
        # force a recache of the message
        await starboard.remove_from_cache(star.message)
        star: Star = await starboard.message(message_id=message_id)
        await star.update_starboard_message()
        await ctx.send(tick(f"The starboard message for the message sent by **{star.author!s}** has been updated"))

    @commands.group(name="starboard")
    @commands.guild_only()
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

    @cmd_starboard.command(name="migrate")
    async def starboard_migrate(self, ctx: RedContext):
        """Trigger a starboard data migration"""
        starboard: GuildStarboard = self.starboard(ctx.guild)
        tmp = await ctx.send("Performing migration... (this may take a while)")
        async with ctx.typing():
            migrated = await starboard.migrate()
        await tmp.delete()
        if migrated == 0:
            await ctx.send(content=warning("No messages were found that needed migration."))
        else:
            await ctx.send(content=tick(f"Successfully migrated {migrated} starboard "
                                        f"message{'s' if migrated > 1 else ''}."))

    @cmd_starboard.command(name="requirerole")
    @cogs_loaded("RequireRole")
    async def starboard_respect_requirerole(self, ctx: RedContext):
        """Toggle whether or not the starboard respects your RequireRole settings"""
        starboard = self.starboard(ctx.guild)
        current = await starboard.guild_config.respect_requirerole()
        current = not current
        await starboard.guild_config.respect_requirerole.set(current)
        await ctx.send("{} respecting RequireRole settings.".format("Now" if current else "No longer"))

    async def on_raw_reaction_add(self, emoji: discord.PartialEmoji, message_id: int, channel_id: int, user_id: int):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return
        # check that the channel is in a guild
        if isinstance(channel, discord.abc.PrivateChannel) or not hasattr(channel, "guild"):
            return
        if not emoji.is_unicode_emoji() or str(emoji) != "\N{WHITE MEDIUM STAR}":
            return
        guild = channel.guild
        starboard: GuildStarboard = self.starboard(guild)
        if await starboard.channel() is None:
            return

        member = guild.get_member(user_id)

        if any([await starboard.is_ignored(member), await starboard.is_ignored(channel)]):
            return

        message = await starboard.message(message_id=message_id, channel=channel, auto_create=True)
        if message is None:
            return
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
        if not emoji.is_unicode_emoji() or str(emoji) != "\N{WHITE MEDIUM STAR}":
            return
        guild = channel.guild
        starboard: GuildStarboard = self.starboard(guild)
        if await starboard.channel() is None:
            return

        member = guild.get_member(user_id)

        if any([await starboard.is_ignored(member), await starboard.is_ignored(channel)]):
            return

        message = await starboard.message(message_id=message_id, channel=channel)
        if not message.has_starred(member):
            return
        try:
            await message.remove_star(member)
        except StarboardException:
            pass

    async def on_raw_reaction_clear(self, message_id: int, channel_id: int):
        channel: discord.TextChannel = self.bot.get_channel(channel_id)
        if channel is None or isinstance(channel_id, discord.abc.PrivateChannel):
            return
        guild = channel.guild
        starboard: GuildStarboard = self.starboard(guild)
        message: Star = await starboard.message(message_id=message_id)
        if message is None:
            return
        message.starrers = []
        if message.starboard_message:
            try:
                await message.starboard_message.delete()
            except (discord.HTTPException, AttributeError):
                pass
        await message.save()

    def __unload(self):
        for task in self._tasks:
            task.cancel()
        # Ensure that all remaining items in the queue are properly handled
        self.bot.loop.create_task(self._empty_starboard_queue())

    async def _task_message_update(self):
        """Task to handle starboard messages. Runs every 10 seconds"""
        while self == self.bot.get_cog("Starboard"):
            for starboard in self.guild_starboard_cache():
                starboard = self.guild_starboard_cache()[starboard]
                try:
                    await starboard.handle_queue()
                except QueueEmpty:
                    pass
            await sleep(10)

    @staticmethod
    async def _handle_messages(starboards: Sequence[GuildStarboard]):
        for starboard in starboards:
            await starboard.handle_queue()

    async def _task_cache_cleanup(self):
        """Task to cleanup starboard message caches. Runs every 15 minutes"""
        while self == self.bot.get_cog("Starboard"):
            for starboard in self.guild_starboard_cache():
                starboard = self.guild_starboard_cache()[starboard]
                await starboard.purge_cache()
            await sleep(15 * 60)

    async def _empty_starboard_queue(self):
        """Post-unload task to empty remaining starboard message update queues"""
        for starboard in self.guild_starboard_cache():
            starboard = self.guild_starboard_cache()[starboard]
            try:
                await starboard.handle_queue()
            except QueueEmpty:
                pass
