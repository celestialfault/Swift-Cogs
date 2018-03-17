import asyncio
from asyncio import sleep

from typing import Sequence

import discord
from discord.ext import commands

from redbot.core import Config, checks, modlog
from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import error, warning

from starboard.classes.guildstarboard import GuildStarboard
from starboard.classes.star import Star
from starboard.classes.base import StarboardBase
from starboard.classes.starboarduser import StarboardUser
from starboard.checks import can_use_starboard, guild_has_starboard, hierarchy_allows, can_migrate
from starboard.exceptions import StarboardException
from starboard.i18n import _

from odinair_libs.checks import cogs_loaded
from odinair_libs.formatting import tick
from odinair_libs.converters import cog_name


class Starboard(StarboardBase):
    """It's almost like pinning messages, except with stars"""

    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = "0.1.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(None, identifier=45351212589, cog_name="Starboard")
        self.config.register_guild(**{
            "blocks": [],
            "ignored_channels": [],
            "channel": None,
            "min_stars": 1,
            "respect_requirerole": False,
            "allow_selfstar": True
        })
        self.config.register_custom("MEMBER_STATS", given={}, received={})
        StarboardBase.bot = self.bot
        StarboardBase.config = self.config
        self._tasks = [
            self.bot.loop.create_task(self._task_cache_cleanup()),
            self.bot.loop.create_task(self._task_message_queue()),
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

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @can_use_starboard()
    async def star(self, ctx: RedContext, message_id: int):
        """Star a message by it's ID"""
        if not await guild_has_starboard(ctx):
            return
        message: Star = await self.get_starboard(ctx.guild).get_message(message_id=message_id, channel=ctx.channel,
                                                                        auto_create=True)
        if not message:
            await ctx.send(_("Sorry, I couldn't find that message."))
            return
        if not message.is_message_valid:
            await ctx.send(
                warning(_("That message cannot be starred as it does not have any content or attachments")),
                delete_after=15)
            return
        if await self.get_starboard(ctx.guild).is_ignored(message.message.author):
            await ctx.send(error(_("The author of that message has been blocked from using this guild's starboard")),
                           delete_after=15)
            return
        if message.has_starred(ctx.author):
            await ctx.send(
                warning(_("You've already starred that message\n\n"
                          "(you can use `{}star remove` to remove your star)").format(ctx.prefix)),
                delete_after=15)
            return
        try:
            await message.add_star(ctx.author)
        except StarboardException as e:
            await ctx.send(warning(_("Failed to add star \N{EM DASH} `{}`").format(e)))
        else:
            await ctx.tick()

    @star.command(name="show")
    async def star_show(self, ctx: RedContext, message_id: int):
        """Show the starboard message for the message given"""
        if not await guild_has_starboard(ctx):
            return
        message: Star = await self.get_starboard(ctx.guild).get_message(message_id=message_id)
        if not message or not message.exists:
            await ctx.send(_("Sorry, I couldn't find that message."))
            return
        await ctx.send(content=message.starboard_content, embed=message.build_embed())

    @star.command(name="remove")
    async def star_remove(self, ctx: RedContext, message_id: int):
        """Remove a previously added star"""
        if not await guild_has_starboard(ctx):
            return
        message = await self.get_starboard(ctx.guild).get_message(message_id=message_id)
        if not message:
            await ctx.send(_("Sorry, I couldn't find that message."))
            return
        if not message.exists:
            await ctx.send(warning(_("That message hasn't been starred by anyone yet")))
            return
        if await self.get_starboard(ctx.guild).is_ignored(message.message.author):
            await ctx.send(error(_("The author of that message has been blocked from using this guild's starboard")),
                           delete_after=15)
            return
        if not message.has_starred(ctx.author):
            await ctx.send(
                warning(_("You haven't starred that message\n\n(you can use `{}star` to star it)")
                        .format(ctx.prefix)),
                delete_after=15)
            return
        try:
            await message.remove_star(ctx.author)
        except StarboardException:
            await ctx.send(warning(_("Failed to remove star")))
        else:
            await ctx.tick()

    @star.command(name="stats", hidden=True)
    async def star_stats(self, ctx: RedContext, member: discord.Member = None, global_stats: bool = False):
        """Get your or a specified member's stats

        If `global_stats` is true, then stats from all the guilds they participate in will be counted.
        Otherwise, only the current guilds stats will be returned.
        """
        member = StarboardUser(self.get_starboard(ctx.guild), member or ctx.author)
        stats = await member.get_stats(global_stats)
        embed = discord.Embed(colour=getattr(ctx.me, "colour", discord.Colour.blurple()))
        embed.set_author(name=_("Stats for {}").format(member), icon_url=member.avatar_url_as(format="png"))
        embed.add_field(name=_("Stars given"), value=_("{} stars").format(stats["given"]))
        embed.add_field(name=_("Stars received"), value=_("{} stars").format(stats["received"]))
        await ctx.send(embed=embed)

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
        star = await self.get_starboard(ctx.guild).get_message(message_id=message_id)
        if not star:
            await ctx.send(error(_("That message either hasn't been starred, or it doesn't exist")))
            return
        if not await star.hide():
            await ctx.send(error(_("That message is already hidden")))
        else:
            await ctx.send(tick(_("The message sent by **{}** is now hidden.").format(star.message.author)))

    @stars.command(name="unhide")
    async def stars_unhide(self, ctx: RedContext, message_id: int):
        """Unhide a previously hidden message"""
        star = await self.get_starboard(ctx.guild).get_message(message_id=message_id)
        if not star:
            await ctx.send(error(_("That message either hasn't been starred, or it doesn't exist")))
            return
        if not await star.unhide():
            await ctx.send(error(_("That message hasn't been hidden")))
        else:
            await ctx.send(tick(_("The message sent by **{}** is no longer hidden.").format(star.message.author)))

    @stars.command(name="block", aliases=["blacklist", "ban"])
    async def stars_block(self, ctx: RedContext, member: discord.Member, *, reason: str = None):
        """Block the passed user from using this guild's starboard

        For ignoring a channel from the starboard, see `[p]starboard ignore`
        """
        if not await hierarchy_allows(self.bot, ctx.author, member):
            await ctx.send(error(_("You aren't allowed to block that member")))
            return
        starboard = self.get_starboard(ctx.guild)
        if await starboard.ignore(member):
            await ctx.tick()
            try:
                await modlog.create_case(ctx.guild, ctx.message.created_at, "starboardblock",
                                         member, ctx.author, reason, until=None, channel=None)
            except RuntimeError:
                pass
        else:
            await ctx.send(error(_("That user is already blocked from using this guild's starboard")))

    @stars.command(name="unblock", aliases=["unblacklist", "unban"])
    async def stars_unblock(self, ctx: RedContext, member: discord.Member, *, reason: str = None):
        """Unblocks the passed user from using this guild's starboard

        For unignoring a channel from the starboard, see `[p]starboard unignore`
        """
        if member.bot:
            await ctx.send(warning(_("Bots are always blocked from using the starboard, and cannot be unblocked")))
            return
        starboard = self.get_starboard(ctx.guild)
        if await starboard.unignore(member):
            await ctx.tick()
            try:
                await modlog.create_case(ctx.guild, ctx.message.created_at, "starboardunblock",
                                         member, ctx.author, reason, until=None, channel=None)
            except RuntimeError:
                pass
        else:
            await ctx.send(warning(_("That user isn't blocked from using this guild's starboard")))

    @stars.command(name="update", hidden=True)
    async def stars_update(self, ctx: RedContext, message_id: int):
        """Force update a starboard message"""
        starboard: GuildStarboard = self.get_starboard(ctx.guild)
        star: Star = await starboard.get_message(message_id=message_id)
        if star is None:
            await ctx.send(warning(_("I couldn't find a message with that ID - has the message been deleted?")))
            return
        # force a recache of the message
        await starboard.remove_from_cache(star.message)
        star: Star = await starboard.get_message(message_id=message_id)
        await star.update_starboard_message()
        await ctx.send(tick(_("The starboard message for the message sent by **{}** has been updated")
                            .format(star.author)))

    @commands.group(name="starboard")
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def cmd_starboard(self, ctx: RedContext):
        """Manage the guild's starboard"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @cmd_starboard.command(name="settings")
    async def starboard_settings(self, ctx: RedContext):
        starboard: GuildStarboard = self.get_starboard(ctx.guild)
        strs = []

        requirerole = _("Cog not loaded") if not cog_name(self.bot, "requirerole")\
            else _("Enabled") if await starboard.guild_config.respect_requirerole() else _("Disabled")
        strs.append(_("RequireRole integration: {}").format(requirerole))
        strs.append(_("Can members self-star: {}").format(_("Yes") if await starboard.selfstar() else _("No")))

        await ctx.send(embed=discord.Embed(colour=discord.Colour.blurple(),
                                           description="\n".join(strs),
                                           title=_("Starboard Settings")))

    @cmd_starboard.command(name="selfstar")
    async def starboard_selfstar(self, ctx: RedContext):
        """Toggles if members can star their own messages"""
        starboard: GuildStarboard = self.get_starboard(ctx.guild)
        current = await starboard.selfstar()
        await starboard.selfstar(not current)
        await ctx.send(_("Members can now star their own messages") if current is False
                       else _("Members can no longer star their own messages"))

    @cmd_starboard.command(name="channel")
    async def starboard_channel(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set or clear the guild's starboard channel"""
        if channel and channel.guild.id != ctx.guild.id:
            await ctx.send(error(_("That channel isn't in this guild")))
            return
        await self.get_starboard(ctx.guild).starboard_channel(channel=channel)
        if channel is None:
            await ctx.send(tick(_("Cleared the current starboard channel")))
        else:
            await ctx.send(tick(_("Set the starboard channel to {}").format(channel.mention)))

    @cmd_starboard.command(name="stars", aliases=["minstars"])
    async def starboard_minstars(self, ctx: RedContext, stars: int):
        """Set the amount of stars required for a message to be sent to this guild's starboard"""
        if stars < 1:
            await ctx.send(error(_("The amount of stars must be a non-zero number")))
            return
        if stars > len(list(filter(lambda x: not x.bot, ctx.guild.members))):
            await ctx.send(error(_("There aren't enough members in this guild to reach that amount of stars")))
            return
        await self.get_starboard(ctx.guild).min_stars(stars)
        await ctx.tick()

    @cmd_starboard.command(name="ignore")
    async def starboard_ignore(self, ctx: RedContext, *, channel: discord.TextChannel):
        """Ignore a channel, preventing any stars from occurring in it

        For ignoring a member from the starboard, see `[p]stars block`
        """
        if await self.get_starboard(ctx.guild).ignore(channel):
            await ctx.tick()
        else:
            await ctx.send(error(_("That channel is already ignored from this guild's starboard")))

    @cmd_starboard.command(name="unignore")
    async def starboard_unignore(self, ctx: RedContext, *, channel: discord.TextChannel):
        """Unignore a channel, allowing stars to occur

        For unignoring a member from the starboard, see `[p]stars unblock`
        """
        if await self.get_starboard(ctx.guild).unignore(channel):
            await ctx.tick()
        else:
            await ctx.send(error(_("That channel isn't ignored from this guild's starboard")))

    @cmd_starboard.command(name="migrate")
    @can_migrate()
    async def starboard_migrate(self, ctx: RedContext):
        """Trigger a starboard data migration

        This command will only be usable if any messages are able to be migrated
        """
        starboard: GuildStarboard = self.get_starboard(ctx.guild)
        tmp = await ctx.send("Performing migration... (this could take a while)")
        async with ctx.typing():
            migrated = await starboard.migrate()
        await tmp.delete()
        await ctx.send(content=tick(_("Successfully migrated {} starboard message(s).").format(migrated)))

    @cmd_starboard.command(name="requirerole")
    @cogs_loaded("RequireRole")
    async def starboard_respect_requirerole(self, ctx: RedContext):
        """Toggle whether or not the starboard respects your RequireRole settings"""
        starboard = self.get_starboard(ctx.guild)
        current = await starboard.guild_config.respect_requirerole()
        current = not current
        await starboard.guild_config.respect_requirerole.set(current)
        if current:
            await ctx.send(_("Now respecting RequireRole settings."))
        else:
            await ctx.send(_("No longer respecting RequireRole settings."))

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
        starboard: GuildStarboard = self.get_starboard(guild)
        if await starboard.starboard_channel() is None:
            return

        member = guild.get_member(user_id)

        if any([await starboard.is_ignored(member), await starboard.is_ignored(channel)]):
            return

        message = await starboard.get_message(message_id=message_id, channel=channel, auto_create=True)
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
        starboard: GuildStarboard = self.get_starboard(guild)
        if await starboard.starboard_channel() is None:
            return

        member = guild.get_member(user_id)

        if any([await starboard.is_ignored(member), await starboard.is_ignored(channel)]):
            return

        message = await starboard.get_message(message_id=message_id, channel=channel)
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
        starboard: GuildStarboard = self.get_starboard(guild)
        message: Star = await starboard.get_message(message_id=message_id)
        if message is None:
            return
        message.starrers = []
        await message.queue_for_update()

    def __unload(self):
        for task in self._tasks:
            task.cancel()
        # Ensure that all remaining items in the queue are properly handled
        self.bot.loop.create_task(self._empty_starboard_queue())

    async def _task_message_queue(self):
        """Task to handle starboard messages. Runs every 10 seconds"""
        await sleep(3)
        while self == self.bot.get_cog('Starboard'):
            await self._empty_starboard_queue()
            await sleep(10)

    @staticmethod
    async def _handle_messages(starboards: Sequence[GuildStarboard]):
        for starboard in starboards:
            await starboard.handle_queue()

    async def _task_cache_cleanup(self):
        """Task to cleanup starboard message caches. Runs every 10 minutes"""
        await sleep(3)
        while self == self.bot.get_cog('Starboard'):
            for starboard in self.get_starboard_cache():
                starboard = self.get_starboard_cache()[starboard]
                await starboard.purge_cache()
            await sleep(10 * 60)

    async def _empty_starboard_queue(self):
        for starboard in self.get_starboard_cache():
            starboard = self.get_starboard_cache()[starboard]
            try:
                await starboard.handle_queue()
            except asyncio.QueueEmpty:
                pass
