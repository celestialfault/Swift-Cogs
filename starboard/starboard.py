import asyncio
from typing import Tuple, Union

import discord
from discord.ext import commands
from discord.raw_models import RawMessageUpdateEvent, RawReactionActionEvent, RawReactionClearEvent

from redbot.core import Config, checks, modlog
from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import error, warning, bold, info, box

from starboard.log import log
from starboard.starboardguild import StarboardGuild
from starboard.starboarduser import StarboardUser
from starboard.checks import can_use_starboard, guild_has_starboard
from starboard.exceptions import StarboardException, SelfStarException
from starboard.base import StarboardBase, get_starboard, setup, get_starboard_cache
from starboard.v2_migration import v2_import, NoMotorException
from starboard.i18n import _

from cog_shared.odinair_libs import cmd_help, fmt, tick, hierarchy_allows, ConfirmMenu, simple_table, chunks


class Starboard(StarboardBase):
    """It's almost like pinning messages, except with stars"""

    __author__ = "odinair <odinair@odinair.xyz>"

    def __init__(self, bot: Red):
        config = Config.get_conf(self, identifier=45351212589, force_registration=True)
        config.register_guild(**{
            "ignored": {
                "members": [],
                "channels": []
            },
            "channel": None,
            "min_stars": 1,
            "selfstar": True
        })

        setup(bot, config)

        self._tasks = (
            self.bot.loop.create_task(self._register_cases()),
            self.bot.loop.create_task(self._init_janitors())
        )  # type: Tuple[asyncio.Task, ...]

    ####################
    #   [p]star

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @can_use_starboard()
    async def star(self, ctx: RedContext, message_id: int):
        """Star a message by it's ID"""
        if not await guild_has_starboard(ctx):
            return
        starboard = await get_starboard(ctx.guild)  # type: StarboardGuild
        message = await starboard.get_message(message_id=message_id, channel=ctx.channel, auto_create=True)
        if not message:
            await ctx.send(_("Sorry, I couldn't find that message."))
            return
        if not message.is_message_valid:
            await ctx.send(
                warning(_("That message cannot be starred as it does not have any content or attachments")),
                delete_after=15)
            return
        if starboard.is_ignored(message.message.author):
            await ctx.send(error(_("The author of that message has been blocked from using this server's starboard")),
                           delete_after=15)
            return
        if message.has_starred(ctx.author):
            await ctx.send(
                warning(_("You've already starred that message\n\n"
                          "(you can use `{}star remove` to remove your star)").format(ctx.prefix)),
                delete_after=15)
            return
        try:
            message.add_star(ctx.author)
        except SelfStarException:
            await ctx.send(warning(_("You cannot star your own messages")))
        except StarboardException:
            await ctx.send(warning(_("Failed to add star")))
        else:
            await ctx.tick()

    @star.command(name="show")
    async def star_show(self, ctx: RedContext, message_id: int):
        """Show the starboard message for the message given"""
        if not await guild_has_starboard(ctx):
            return
        starboard = await get_starboard(ctx.guild)  # type: StarboardGuild
        message = await starboard.get_message(message_id=message_id)
        if not message:
            await ctx.send(_("Sorry, I couldn't find that message."))
            return
        await ctx.send(**message.starboard_message_contents)

    @star.command(name="remove")
    async def star_remove(self, ctx: RedContext, message_id: int):
        """Remove a previously added star"""
        if not await guild_has_starboard(ctx):
            return
        starboard = await get_starboard(ctx.guild)  # type: StarboardGuild
        message = await starboard.get_message(message_id=message_id)
        if not message:
            await ctx.send(_("Sorry, I couldn't find that message."))
            return
        if starboard.is_ignored(message.message.author):
            await ctx.send(error(_("The author of that message has been blocked from using this server's starboard")),
                           delete_after=15)
            return
        if not message.has_starred(ctx.author):
            await fmt(ctx, warning(_("You haven't starred that message\n\n(you can use `{prefix}star` to star it)")),
                      delete_after=15)
            return
        try:
            message.remove_star(ctx.author)
        except StarboardException:
            await ctx.send(warning(_("Failed to remove star")))
        else:
            await ctx.tick()

    @staticmethod
    async def _send_stats(ctx: RedContext, stats: Tuple[int, int, int], member: discord.Member = None):
        member = member or ctx.author
        desc = _("Stats for member {member}:\n\n"
                 "\N{RIGHTWARDS BLACK CIRCLED WHITE ARROW} **{given}** stars given\n"
                 "\N{RIGHTWARDS BLACK CIRCLED WHITE ARROW} **{received}** stars received\n"
                 "\N{RIGHTWARDS BLACK CIRCLED WHITE ARROW} **{msgs}** starboard messages") \
            .format(member="{member}", given=stats[0], received=stats[1], msgs=stats[2])
        if await ctx.embed_requested():
            embed = discord.Embed(colour=getattr(ctx.me, "colour", discord.Colour.blurple()),
                                  description=desc.format(member=member.mention))
            embed.set_author(name=_("Starboard Stats"), icon_url=member.avatar_url_as(format="png"))
            await ctx.send(embed=embed)
        else:
            await ctx.send(info(desc.format(member=bold(str(member)))))

    @star.command(name="stats")
    async def star_stats(self, ctx: RedContext, *, member: discord.Member = None):
        """Get your or a specified member's stats"""
        await self._send_stats(ctx, await StarboardUser(await get_starboard(ctx.guild),
                                                        member or ctx.author).get_stats(), member)

    @star.command(name="gstats")
    async def star_gstats(self, ctx: RedContext, *, member: discord.Member = None):
        """Retrieve your or the specified member's statistics across *all* guilds"""
        await self._send_stats(ctx, await StarboardUser.get_global_stats(self.bot, member or ctx.author), member)

    @star.command(name="leaderboard")
    async def star_leaderboard(self, ctx: RedContext):
        """Retrieve the star leaderboard for the current guild"""
        given, received, messages = await StarboardUser.leaderboard(ctx.guild)
        given, received = (list(given.items())[:10], list(received.items())[:10])

        messages_ = list(chunks(list(messages.items())[:20], 2))
        keys = list(messages.keys())
        messages_1 = [x[0] for x in messages_]
        messages_2 = [x[1] for x in messages_ if len(x) == 2]

        if not given or not received:
            await ctx.send(warning(_("No one has any recorded stars yet! Go star some messages first!")))
            return

        def index(seq: Union[list, dict], item):
            if isinstance(seq, dict):
                seq = list(seq.items())
            item = seq.index(item) + 1
            total_len = len(str(len(seq)))
            padding = "0" * (total_len - len(str(item)))
            return "{}{}".format(padding, item)

        fmt_str = "**`{index}.`** {member} \N{EM DASH} **{stars}** \N{WHITE MEDIUM STAR}"
        given = "\n".join([fmt_str.format(index=index(given, (x, y)), member=x.mention, stars=y)
                           for x, y in given])
        received = "\n".join([fmt_str.format(index=index(received, (x, y)), member=x.mention, stars=y)
                              for x, y in received])

        msg_fmt = "**`{index}.`** {member} \N{EM DASH} **{messages}**"
        messages = [
            "\n".join([
                msg_fmt.format(index=index(keys, x), member=x.mention, messages=y) for x, y in messages_1
            ]),
            "\n".join([
                msg_fmt.format(index=index(keys, x), member=x.mention, messages=y) for x, y in messages_2
            ])
        ]

        embed = discord.Embed(colour=ctx.me.colour)
        embed.set_author(name=_("Leaderboard"), icon_url=ctx.guild.icon_url)
        embed.add_field(name=_("Stars Given"), value=given)
        embed.add_field(name=_("Stars Received"), value=received)

        embed.add_field(name="\N{ZERO WIDTH JOINER}", value="\N{ZERO WIDTH JOINER}", inline=False)

        embed.add_field(name=_("Starboard Messages"), value=messages[0])
        embed.add_field(name="\N{ZERO WIDTH JOINER}", value=messages[1])

        await ctx.send(embed=embed)

    ####################
    #   [p]stars

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
        starboard = await get_starboard(ctx.guild)  # type: StarboardGuild
        star = await starboard.get_message(message_id=message_id)
        if not star:
            await ctx.send(error(_("That message either hasn't been starred, or it doesn't exist")))
            return
        if star.hidden:
            await ctx.send(error(_("That message is already hidden")))
        else:
            star.hidden = True
            await ctx.send(tick(_("The message sent by **{}** is now hidden.").format(star.message.author)))

    @stars.command(name="unhide")
    async def stars_unhide(self, ctx: RedContext, message_id: int):
        """Unhide a previously hidden message"""
        starboard = await get_starboard(ctx.guild)  # type: StarboardGuild
        star = await starboard.get_message(message_id=message_id)
        if not star:
            await ctx.send(error(_("That message either hasn't been starred, or it doesn't exist")))
            return
        if star.hidden is False:
            await ctx.send(error(_("That message hasn't been hidden")))
        else:
            star.hidden = False
            await ctx.send(tick(_("The message sent by **{}** is no longer hidden.").format(star.message.author)))

    @stars.command(name="block", aliases=["blacklist"])
    async def stars_block(self, ctx: RedContext, member: discord.Member, *, reason: str = None):
        """Block the passed user from using this guild's starboard

        Bot accounts are always blocked from using the starboard, and cannot be manually blocked.

        For ignoring a channel from the starboard, see `[p]starboard ignore`"""
        if member.bot:
            await ctx.send(warning(_("Bot accounts are always blocked from using the starboard, "
                                     "and cannot be manually blocked nor unblocked.")))
            return
        if not await hierarchy_allows(self.bot, ctx.author, member):
            await ctx.send(error(_("You aren't allowed to block that member")))
            return
        starboard = await get_starboard(ctx.guild)  # type: StarboardGuild
        if starboard.ignore(member):
            await ctx.tick()
            try:
                await modlog.create_case(self.bot, ctx.guild, ctx.message.created_at, "starboardblock",
                                         member, ctx.author, reason, until=None, channel=None)
            except RuntimeError:
                pass
        else:
            await ctx.send(error(_("That user is already blocked from using this server's starboard")))

    @stars.command(name="unblock", aliases=["unblacklist"])
    async def stars_unblock(self, ctx: RedContext, member: discord.Member, *, reason: str = None):
        """Unblocks the passed user from using this guild's starboard

        Bot accounts are always blocked from using the starboard, and cannot be manually unblocked.

        For unignoring a channel from the starboard, see `[p]starboard unignore`"""
        if member.bot:
            await ctx.send(warning(_("Bot accounts are always blocked from using the starboard, "
                                     "and cannot be manually blocked nor unblocked.")))
            return
        starboard = await get_starboard(ctx.guild)  # type: StarboardGuild
        if starboard.unignore(member):
            await ctx.tick()
            try:
                await modlog.create_case(self.bot, ctx.guild, ctx.message.created_at, "starboardunblock",
                                         member, ctx.author, reason, until=None, channel=None)
            except RuntimeError:
                pass
        else:
            await ctx.send(warning(_("That user isn't blocked from using this server's starboard")))

    @stars.command(name="update")
    async def stars_update(self, ctx: RedContext, message_id: int):
        """Forcefully update a starboard message

        `message_id` should be the corresponding message that the starboard message
        is for, and not the starboard message itself."""
        starboard = await get_starboard(ctx.guild)  # type: StarboardGuild
        star = await starboard.get_message(message_id=message_id)
        if star is None:
            await ctx.send(warning(_("I couldn't find a message with that ID - has the message been deleted?")))
            return
        await star.update_cached_message()
        await star.update_starboard_message()
        await ctx.send(tick(_("The starboard message for the message sent by **{}** has been updated")
                            .format(star.author)))

    ####################
    #   [p]starboardset

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
        if you're importing a local v2 instance."""
        disclaimer = _(
            "Are you sure you want to import your v2 instances data?\n\n"
            "Guild settings will not be imported and must be setup again.\n\n"
            "Any messages starred previous to this import that are also present "
            "in the v2 data **will be overwritten.**\n\n"
            "Please click \N{WHITE HEAVY CHECK MARK} if you wish to continue."
        )
        disclaimer = discord.Embed(description=disclaimer, colour=discord.Colour.gold(), title=_("V2 Data Import"))

        async with ConfirmMenu(ctx, embed=disclaimer) as result:
            if not result:
                await ctx.send(_("Import cancelled."), delete_after=30)
                return
            tmp = await ctx.send(_("Importing data... (this could take a while)"))
            try:
                async with ctx.typing():
                    await v2_import(self.bot, mongo_uri)
            except NoMotorException:
                await tmp.delete()
                await fmt(ctx, error(_("Motor is not installed; cannot import v2 data.\n\n"
                                       "Please use `{prefix}pipinstall motor` and restart your bot, "
                                       "and re-attempt the import.")))
            else:
                await tmp.delete()
                await ctx.send(tick(_("Successfully imported v2 data")))

    ####################
    #   [p]starboard

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
        starboard = await get_starboard(ctx.guild)  # type: StarboardGuild

        ignores = {x: len(y) for x, y in starboard.ignored.items()}

        strs = simple_table(
            [
                _("Min number of stars:"),
                _("Ignored channels:"),
                _("Ignored members:"),
                _("Can members self-star:"),
                _("Message cache length:")
            ],
            ["[{}]".format(x) for x in [
                starboard.min_stars,
                ignores["channels"],
                ignores["members"],
                _("Yes") if starboard.selfstar else _("No"),
                len(starboard.message_cache)
            ]]
        )

        strs = ["Starboard channel: {}"
                "".format(getattr(starboard.channel, "mention", _("No channel set"))),
                box("\n".join(strs), lang="ini")]

        await ctx.send(embed=discord.Embed(title=_("Starboard Settings"), description="\n".join(strs),
                                           colour=ctx.me.colour))

    @cmd_starboard.command(name="selfstar")
    async def starboard_selfstar(self, ctx: RedContext, toggle: bool = None):
        """Toggles if members can star their own messages

        Please note that user statistics are not updated if a member stars their own messages,
        regardless of if this setting is enabled or not."""
        starboard = await get_starboard(ctx.guild)  # type: StarboardGuild
        toggle = (not starboard.selfstar) if toggle is None else toggle
        starboard.selfstar = toggle
        await ctx.send(tick(_("Members can now star their own messages") if toggle
                            else _("Members can no longer star their own messages")))

    @cmd_starboard.command(name="channel")
    async def starboard_channel(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set or clear the guild's starboard channel"""
        if channel and channel.guild.id != ctx.guild.id:
            await ctx.send(error(_("That channel isn't in this server")))
            return
        starboard = await get_starboard(ctx.guild)  # type: StarboardGuild
        starboard.channel = channel
        if channel is None:
            await ctx.send(tick(_("Cleared the current starboard channel")))
        else:
            await ctx.send(tick(_("Set the starboard channel to {}").format(channel.mention)))

    @cmd_starboard.command(name="minstars", aliases=["stars"])
    async def starboard_minstars(self, ctx: RedContext, stars: int):
        """Set the amount of stars required for a message to be sent to this guild's starboard"""
        if stars < 1:
            await ctx.send(warning(_("The amount of stars must be a non-zero number")))
            return
        if stars > len(list(filter(lambda x: not x.bot, ctx.guild.members))):
            await ctx.send(warning(_("There aren't enough members in this server to reach that amount of stars")))
            return
        starboard = await get_starboard(ctx.guild)  # type: StarboardGuild
        starboard.min_stars = stars
        await ctx.tick()

    @cmd_starboard.command(name="ignore")
    async def starboard_ignore(self, ctx: RedContext, *, channel: discord.TextChannel):
        """Ignore a channel, preventing any stars from occurring in it

        For ignoring a member from the starboard, see `[p]stars block`"""
        if (await get_starboard(ctx.guild)).ignore(channel):
            await ctx.tick()
        else:
            await ctx.send(warning(_("That channel is already ignored from this server's starboard")))

    @cmd_starboard.command(name="unignore")
    async def starboard_unignore(self, ctx: RedContext, *, channel: discord.TextChannel):
        """Unignore a channel, allowing stars to occur

        For unignoring a member from the starboard, see `[p]stars unblock`"""
        if (await get_starboard(ctx.guild)).unignore(channel):
            await ctx.tick()
        else:
            await ctx.send(warning(_("That channel isn't ignored from this server's starboard")))

    ##################################################################################
    #   Init tasks

    async def _init_janitors(self):
        """Guild janitor management task"""
        await self.bot.wait_until_ready()
        try:
            while True:
                for guild in self.bot.guilds:
                    starboard = await get_starboard(guild)
                    if starboard.channel:
                        starboard.setup_janitor()
                await asyncio.sleep(3 * 60)
        except asyncio.CancelledError:
            log.debug("Cleaning up janitor tasks...")
            for starboard in get_starboard_cache().values():
                task = starboard.janitor_task
                if task:
                    task.cancel()

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

    def __unload(self):
        # janitor tasks are cancelled by _init_janitors
        for task in self._tasks:
            task.cancel()

    ##################################################################################
    #   Event listeners

    # noinspection PyMethodMayBeStatic
    async def on_guild_join(self, guild: discord.Guild):
        (await get_starboard(guild)).setup_janitor()

    # noinspection PyMethodMayBeStatic
    async def on_guild_remove(self, guild: discord.Guild):
        starboard = await get_starboard(guild)
        if starboard.janitor_task:
            starboard.janitor_task.cancel()

    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        channel = self.bot.get_channel(payload.data['channel_id'])
        if isinstance(channel, (discord.abc.PrivateChannel, type(None))):
            return
        guild = channel.guild
        starboard = await get_starboard(guild)  # type: StarboardGuild
        message = await starboard.get_message(message_id=payload.message_id, cache_only=True)
        if message is not None:
            await message.update_cached_message()
            message.queue_for_update()

    async def _starboard_msg(self, payload: RawReactionActionEvent, *, fn: str, auto_create: bool = False):
        emoji = payload.emoji  # type: discord.PartialEmoji
        if not all([emoji.is_unicode_emoji(), str(emoji) == "\N{WHITE MEDIUM STAR}"]):
            return

        channel = self.bot.get_channel(payload.channel_id)  # type: discord.TextChannel
        if channel is None or isinstance(channel, discord.abc.PrivateChannel) or not getattr(channel, "guild", None):
            return

        guild = channel.guild  # type: discord.Guild
        starboard = await get_starboard(guild)  # type: StarboardGuild
        if starboard.channel is None:
            return

        member = guild.get_member(payload.user_id)
        if any([starboard.is_ignored(member), starboard.is_ignored(channel)]):
            return

        message = await starboard.get_message(message_id=payload.message_id, channel=channel, auto_create=auto_create)
        if message is None:
            return

        try:
            getattr(message, fn)(member)
        except SelfStarException:
            if channel.permissions_for(channel.guild.me).manage_messages:
                try:
                    await message.message.remove_reaction(emoji=emoji, member=member)
                except discord.HTTPException:
                    pass
        except StarboardException:
            pass

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        await self._starboard_msg(payload, auto_create=True, fn="add_star")

    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        await self._starboard_msg(payload, fn="remove_star")

    async def on_raw_reaction_clear(self, payload: RawReactionClearEvent):
        channel = self.bot.get_channel(payload.channel_id)  # type: discord.TextChannel
        if channel is None or isinstance(channel, discord.abc.PrivateChannel):
            return
        guild = channel.guild
        starboard = await get_starboard(guild)  # type: StarboardGuild
        message = await starboard.get_message(message_id=payload.message_id)
        if message is None:
            return
        message.starrers = []
        message.queue_for_update()
