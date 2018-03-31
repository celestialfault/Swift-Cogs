import asyncio
from asyncio import sleep

import discord
from discord.ext import commands

from redbot.core import Config, checks, modlog
from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import error, warning

from starboard.starboardmessage import StarboardMessage
from starboard.starboardguild import StarboardGuild
from starboard.starboarduser import StarboardUser
from starboard.checks import can_use_starboard, guild_has_starboard, hierarchy_allows, can_migrate
from starboard.exceptions import StarboardException, SelfStarException
from starboard.base import StarboardBase, get_starboard, get_starboard_cache, setup
from starboard.v2_migration import v2_import
from starboard.i18n import _

from cog_shared.odinair_libs.formatting import tick, cmd_help
from cog_shared.odinair_libs.checks import cogs_loaded
from cog_shared.odinair_libs.converters import cog_name
from cog_shared.odinair_libs.menus import confirm


class Starboard(StarboardBase):
    """It's almost like pinning messages, except with stars"""

    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = "1.0.0"

    def __init__(self, bot: Red):
        config = Config.get_conf(self, identifier=45351212589, force_registration=True)
        config.register_guild(**{
            "ignored": {
                "members": [],
                "channels": []
            },
            "channel": None,
            "min_stars": 1,
            "requirerole": False,
            "selfstar": True,
            "messages": []  # this is only around for legacy purposes
        })
        config.register_member(given={}, received={})

        setup(bot, config)

        self._tasks = (
            self.bot.loop.create_task(self._task_cache_cleanup()),
            self.bot.loop.create_task(self._task_message_queue()),
            self.bot.loop.create_task(self._register_cases())
        )

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
        starboard: StarboardGuild = await get_starboard(ctx.guild)
        message: StarboardMessage = await starboard.get_message(message_id=message_id, channel=ctx.channel,
                                                                auto_create=True)
        if not message:
            await ctx.send(_("Sorry, I couldn't find that message."))
            return
        if not message.is_message_valid:
            await ctx.send(
                warning(_("That message cannot be starred as it does not have any content or attachments")),
                delete_after=15)
            return
        if await starboard.is_ignored(message.message.author):
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
        except SelfStarException:
            await ctx.send(warning(_("You cannot star your own messages")))
        except StarboardException as e:
            await ctx.send(warning(_("Failed to add star \N{EM DASH} `{}`").format(e)))
        else:
            await ctx.tick()

    @star.command(name="show")
    async def star_show(self, ctx: RedContext, message_id: int):
        """Show the starboard message for the message given"""
        if not await guild_has_starboard(ctx):
            return
        starboard: StarboardGuild = await get_starboard(ctx.guild)
        message: StarboardMessage = await starboard.get_message(message_id=message_id)
        if not message:
            await ctx.send(_("Sorry, I couldn't find that message."))
            return
        await ctx.send(content=message.starboard_content, embed=message.build_embed())

    @star.command(name="remove")
    async def star_remove(self, ctx: RedContext, message_id: int):
        """Remove a previously added star"""
        if not await guild_has_starboard(ctx):
            return
        starboard: StarboardGuild = await get_starboard(ctx.guild)
        message = await starboard.get_message(message_id=message_id)
        if not message:
            await ctx.send(_("Sorry, I couldn't find that message."))
            return
        if await starboard.is_ignored(message.message.author):
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

    @star.command(name="stats")
    async def star_stats(self, ctx: RedContext, member: discord.Member = None, global_stats: bool = False):
        """Get your or a specified member's stats

        If `global_stats` is true, then stats from all the guilds a user participates in will be counted.
        Otherwise, only the current guild will be accounted for.
        """
        member = member or ctx.author
        stats = StarboardUser(await get_starboard(ctx.guild), member)
        stats = await stats.get_stats(global_stats)
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
        star: StarboardMessage = await (await get_starboard(ctx.guild)).get_message(message_id=message_id)
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
        star: StarboardMessage = await (await get_starboard(ctx.guild)).get_message(message_id=message_id)
        if not star:
            await ctx.send(error(_("That message either hasn't been starred, or it doesn't exist")))
            return
        if not await star.unhide():
            await ctx.send(error(_("That message hasn't been hidden")))
        else:
            await ctx.send(tick(_("The message sent by **{}** is no longer hidden.").format(star.message.author)))

    @stars.command(name="block", aliases=["blacklist"])
    async def stars_block(self, ctx: RedContext, member: discord.Member, *, reason: str = None):
        """Block the passed user from using this guild's starboard

        For ignoring a channel from the starboard, see `[p]starboard ignore`
        """
        if not await hierarchy_allows(self.bot, ctx.author, member):
            await ctx.send(error(_("You aren't allowed to block that member")))
            return
        starboard: StarboardGuild = await get_starboard(ctx.guild)
        if await starboard.ignore(member):
            await ctx.tick()
            try:
                await modlog.create_case(self.bot, ctx.guild, ctx.message.created_at, "starboardblock",
                                         member, ctx.author, reason, until=None, channel=None)
            except RuntimeError:
                pass
        else:
            await ctx.send(error(_("That user is already blocked from using this guild's starboard")))

    @stars.command(name="unblock", aliases=["unblacklist"])
    async def stars_unblock(self, ctx: RedContext, member: discord.Member, *, reason: str = None):
        """Unblocks the passed user from using this guild's starboard

        For unignoring a channel from the starboard, see `[p]starboard unignore`
        """
        if member.bot:
            await ctx.send(warning(_("Bots are always blocked from using the starboard, and cannot be unblocked")))
            return
        starboard: StarboardGuild = await get_starboard(ctx.guild)
        if await starboard.unignore(member):
            await ctx.tick()
            try:
                await modlog.create_case(self.bot, ctx.guild, ctx.message.created_at, "starboardunblock",
                                         member, ctx.author, reason, until=None, channel=None)
            except RuntimeError:
                pass
        else:
            await ctx.send(warning(_("That user isn't blocked from using this guild's starboard")))

    @stars.command(name="update", hidden=True)
    async def stars_update(self, ctx: RedContext, message_id: int):
        """Force update a starboard message"""
        starboard: StarboardGuild = await get_starboard(ctx.guild)
        star: StarboardMessage = await starboard.get_message(message_id=message_id)
        if star is None:
            await ctx.send(warning(_("I couldn't find a message with that ID - has the message been deleted?")))
            return
        await star.update_cached_message()
        await star.update_starboard_message()
        await ctx.send(tick(_("The starboard message for the message sent by **{}** has been updated")
                            .format(star.author)))

    @commands.group(name="starboardset")
    @checks.is_owner()
    async def starboardset(self, ctx: RedContext):
        """Core Starboard cog management"""
        await cmd_help(ctx)

    @starboardset.command(name="v2_import")
    @checks.is_owner()
    async def starboardset_v2_import(self, ctx: RedContext, mongo_uri: str):
        """Import Red v2 instance data

        Only messages are imported currently; guild settings are not imported,
        and must be setup again.

        In most cases, `mongodb://localhost:27017` will work just fine
        if you're importing a local v2 instance.
        """
        if not await confirm(ctx, message=_("Are you sure you want to import your v2 instances data?\n\n"
                                            "Guild settings will not be imported and must be setup again.\n\n"
                                            "Any messages starred previous to this import that are also present "
                                            "in the v2 data **will be overwritten.**"),
                             colour=discord.Colour.red()):
            await ctx.send(_("Okay then."), delete_after=30)
            return
        tmp = await ctx.send(_("Importing data... (this could take a while)"))
        async with ctx.typing():
            await v2_import(self.bot, mongo_uri)
        await tmp.delete()
        await ctx.send(tick(_("Successfully imported v2 data")))

    @commands.group(name="starboard")
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def cmd_starboard(self, ctx: RedContext):
        """Manage the guild's starboard"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @cmd_starboard.command(name="settings")
    async def starboard_settings(self, ctx: RedContext):
        """Get the current settings for this guild's starboard"""
        starboard: StarboardGuild = await get_starboard(ctx.guild)
        requirerole = _("Cog not loaded") if not cog_name(self.bot, "requirerole")\
            else _("Enabled") if await starboard.guild_config.respect_requirerole() else _("Disabled")

        strs = (
            _("Starboard channel: {}").format(getattr(await starboard.starboard_channel(), "mention", _("None"))),
            _("Min # of stars: {}").format(await starboard.min_stars()),
            _("RequireRole integration: {}").format(requirerole),
            _("Can members self-star: {}").format(_("Yes") if await starboard.selfstar() else _("No"))
        )

        await ctx.send(embed=discord.Embed(title=_("Starboard Settings"), description="\n".join(strs),
                                           colour=discord.Colour.blurple()))

    @cmd_starboard.command(name="selfstar")
    async def starboard_selfstar(self, ctx: RedContext):
        """Toggles if members can star their own messages"""
        starboard: StarboardGuild = await get_starboard(ctx.guild)
        current = await starboard.selfstar()
        await starboard.selfstar(not current)
        await ctx.send(tick(_("Members can now star their own messages") if current is False
                            else _("Members can no longer star their own messages")))

    @cmd_starboard.command(name="channel")
    async def starboard_channel(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set or clear the guild's starboard channel"""
        if channel and channel.guild.id != ctx.guild.id:
            await ctx.send(error(_("That channel isn't in this guild")))
            return
        await (await get_starboard(ctx.guild)).starboard_channel(channel=channel)
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
        await (await get_starboard(ctx.guild)).min_stars(stars)
        await ctx.tick()

    @cmd_starboard.command(name="ignore")
    async def starboard_ignore(self, ctx: RedContext, *, channel: discord.TextChannel):
        """Ignore a channel, preventing any stars from occurring in it

        For ignoring a member from the starboard, see `[p]stars block`
        """
        if await (await get_starboard(ctx.guild)).ignore(channel):
            await ctx.tick()
        else:
            await ctx.send(error(_("That channel is already ignored from this guild's starboard")))

    @cmd_starboard.command(name="unignore")
    async def starboard_unignore(self, ctx: RedContext, *, channel: discord.TextChannel):
        """Unignore a channel, allowing stars to occur

        For unignoring a member from the starboard, see `[p]stars unblock`
        """
        if await (await get_starboard(ctx.guild)).unignore(channel):
            await ctx.tick()
        else:
            await ctx.send(error(_("That channel isn't ignored from this guild's starboard")))

    @cmd_starboard.command(name="migrate")
    @can_migrate()
    async def starboard_migrate(self, ctx: RedContext):
        """Trigger a starboard data migration

        This command will only be usable if any messages are able to be migrated
        """
        starboard: StarboardGuild = await get_starboard(ctx.guild)
        tmp = await ctx.send("Performing migration... (this could take a while)")
        async with ctx.typing():
            migrated = await starboard.migrate()
        await tmp.delete()
        await ctx.send(content=tick(_("Successfully migrated {} starboard message(s).").format(migrated)))

    @cmd_starboard.command(name="requirerole")
    @cogs_loaded("RequireRole")
    async def starboard_respect_requirerole(self, ctx: RedContext):
        """Toggle whether or not the starboard respects your RequireRole settings"""
        starboard: StarboardGuild = await get_starboard(ctx.guild)
        new_val = not await starboard.requirerole()
        await starboard.requirerole(new_val)
        if new_val:
            await ctx.send(tick(_("Now respecting RequireRole settings.")))
        else:
            await ctx.send(tick(_("No longer respecting RequireRole settings.")))

    async def on_raw_message_edit(self, message_id: int, data: dict):
        channel = self.bot.get_channel(data.get("channel_id"))
        if isinstance(channel, (discord.abc.PrivateChannel, type(None))):
            return
        guild = channel.guild
        starboard: StarboardGuild = await get_starboard(guild)
        msg: StarboardMessage = await starboard.get_message(message_id=message_id, cache_only=True)
        if msg is not None:
            await msg.update_cached_message()
            await msg.queue_for_update()

    async def on_raw_reaction_add(self, emoji: discord.PartialEmoji, message_id: int, channel_id: int, user_id: int):
        channel: discord.TextChannel = self.bot.get_channel(channel_id)
        if channel is None:
            return
        # check that the channel is in a guild
        if isinstance(channel, discord.abc.PrivateChannel) or not getattr(channel, "guild", None):
            return
        if not emoji.is_unicode_emoji() or str(emoji) != "\N{WHITE MEDIUM STAR}":
            return
        guild: discord.Guild = channel.guild
        starboard: StarboardGuild = await get_starboard(guild)
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
        except SelfStarException:
            if channel.permissions_for(guild.me).manage_messages:
                try:
                    await message.message.remove_reaction(emoji=emoji, member=member)
                except discord.HTTPException:
                    pass
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
        starboard: StarboardGuild = await get_starboard(guild)
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
        starboard: StarboardGuild = await get_starboard(guild)
        message: StarboardMessage = await starboard.get_message(message_id=message_id)
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

    async def _task_cache_cleanup(self):
        """Task to cleanup starboard message caches. Runs every 10 minutes"""
        await sleep(3)
        while self == self.bot.get_cog('Starboard'):
            for starboard in get_starboard_cache():
                starboard = get_starboard_cache()[starboard]
                await starboard.purge_cache()
            await sleep(10 * 60)

    @staticmethod
    async def _empty_starboard_queue():
        for starboard in get_starboard_cache():
            starboard = get_starboard_cache()[starboard]
            try:
                await starboard.handle_queue()
            except asyncio.QueueEmpty:
                pass
