import asyncio
from typing import Tuple, Dict, Union

import discord
from discord.ext import commands
from discord.raw_models import RawMessageUpdateEvent, RawReactionActionEvent, RawReactionClearEvent
from redbot.core import Config, checks, modlog
from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import error, warning, bold, info, inline, pagify
from tabulate import tabulate

from cog_shared.odinair_libs import (
    cmd_help,
    fmt,
    tick,
    hierarchy_allows,
    ConfirmMenu,
    format_int,
    index,
    slice_dict,
)
from starboard import stats
from starboard.base import StarboardBase, get_starboard, setup, get_starboard_cache
from starboard.checks import can_use_starboard, guild_has_starboard
from starboard.exceptions import StarboardException, SelfStarException
from starboard.i18n import i18n
from starboard.log import log
from starboard.starboardguild import StarboardGuild
from starboard.v2_migration import v2_import, NoMotorException


class Starboard(StarboardBase):
    """It's almost like pinning messages, except with stars"""

    __author__ = "odinair <odinair@odinair.xyz>"

    def __init__(self, bot: Red):
        config = Config.get_conf(self, identifier=45351212589, force_registration=True)
        config.register_guild(
            **{
                "ignored": {"members": [], "channels": []},
                "channel": None,
                "min_stars": 1,
                "selfstar": True,
            }
        )

        setup(bot, config)

        self._tasks = (
            self.bot.loop.create_task(self._register_cases()),
            self.bot.loop.create_task(self._init_janitors()),
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
        starboard = get_starboard(ctx.guild)  # type: StarboardGuild
        message = await starboard.get_message(
            message_id=message_id, channel=ctx.channel, auto_create=True
        )
        if not message:
            await ctx.send(i18n("Sorry, I couldn't find that message."))
            return
        if not message.is_message_valid:
            await ctx.send(
                warning(
                    i18n(
                        "That message cannot be starred as it does not have any "
                        "content or attachments"
                    )
                ),
                delete_after=15,
            )
            return
        if await starboard.is_ignored(message.message.author):
            await ctx.send(
                warning(
                    i18n(
                        "The author of that message has been blocked from using "
                        "this server's starboard"
                    )
                ),
                delete_after=15,
            )
            return
        if message.has_starred(ctx.author):
            await ctx.send(
                warning(
                    i18n(
                        "You've already starred that message\n\n"
                        "(you can use `{}star remove` to remove your star)"
                    ).format(
                        ctx.prefix
                    )
                ),
                delete_after=15,
            )
            return
        try:
            await message.add_star(ctx.author)
        except SelfStarException:
            await ctx.send(warning(i18n("You cannot star your own messages")))
        except StarboardException:
            await ctx.send(warning(i18n("Failed to add star")))
        else:
            await ctx.tick()

    @star.command(name="show")
    async def star_show(self, ctx: RedContext, message_id: int):
        """Show the starboard message for the message given"""
        if not await guild_has_starboard(ctx):
            return
        starboard = get_starboard(ctx.guild)  # type: StarboardGuild
        message = await starboard.get_message(message_id=message_id)
        if not message or message.stars == 0:
            await ctx.send(i18n("Sorry, I couldn't find that message."))
            return
        if not message.is_message_valid:
            await ctx.send(warning(i18n("That message cannot be displayed on the starboard")))
            return
        await ctx.send(**message.starboard_message_contents)

    @star.command(name="remove", aliases=["rm"])
    async def star_remove(self, ctx: RedContext, message_id: int):
        """Remove a previously added star"""
        if not await guild_has_starboard(ctx):
            return
        starboard = get_starboard(ctx.guild)  # type: StarboardGuild
        message = await starboard.get_message(message_id=message_id)
        if not message:
            await ctx.send(i18n("Sorry, I couldn't find that message."))
            return
        if await starboard.is_ignored(message.message.author):
            await ctx.send(
                error(
                    i18n(
                        "The author of that message has been blocked from using "
                        "this server's starboard"
                    )
                ),
                delete_after=15,
            )
            return
        if not message.has_starred(ctx.author):
            await fmt(
                ctx,
                warning(
                    i18n(
                        "You haven't starred that message\n\n"
                        "(you can use `{prefix}star` to star it)"
                    )
                ),
                delete_after=15,
            )
            return
        try:
            await message.remove_star(ctx.author)
        except StarboardException:
            await ctx.send(warning(i18n("Failed to remove star")))
        else:
            await ctx.tick()

    @star.command(name="stats")
    async def star_stats(self, ctx: RedContext, *, member: discord.Member = None):
        """Get your or a specified member's stats"""
        member = member or ctx.author
        data_unparsed = await stats.user_stats(member)
        data = {k: format_int(v) for k, v in data_unparsed.items()}  # type: Dict[str, str]
        positions = await stats.leaderboard_position(member)

        if await ctx.embed_requested():
            embed = discord.Embed(colour=ctx.me.colour)

            embed.add_field(
                name=i18n("Stars Given"),
                value=i18n("**{} stars** (position {})").format(data["given"], positions["given"]),
            )
            embed.add_field(
                name=i18n("Stars Received"),
                value=i18n("**{} stars** (position {})").format(
                    data["received"], positions["received"]
                ),
            )
            embed.add_field(
                name=i18n("Starboard Messages"),
                value=i18n("**{} messages** (position {})").format(
                    data["messages"], positions["messages"]
                ),
            )

            embed.set_author(
                name=i18n("Starboard Stats"), icon_url=member.avatar_url_as(format="png")
            )
            await ctx.send(embed=embed)
        else:
            positions = {"{}_pos".format(k): v for k, v in positions.items()}
            desc = i18n(
                "Stats for member {member}:"
                "\n"
                "\n"
                "\N{RIGHTWARDS BLACK CIRCLED WHITE ARROW} **{given}** stars given "
                "(position {given_pos})"
                "\n"
                "\N{RIGHTWARDS BLACK CIRCLED WHITE ARROW} **{received}** stars received "
                "(position {received_pos})"
                "\n"
                "\N{RIGHTWARDS BLACK CIRCLED WHITE ARROW} **{messages}** starboard messages "
                "(position {messages_pos})"
            ).format(
                member=bold(str(member)), **data, **positions
            )
            await ctx.send(info(desc))

    @star.command(name="leaderboard", aliases=["lb"])
    async def star_leaderboard(self, ctx: RedContext):
        """Retrieve the star leaderboard for the current guild"""
        data = await stats.leaderboard(ctx.guild, top=10)
        if await ctx.embed_requested():
            default_str = inline(i18n("There's nothing here yet..."))
            msg_keys = list(data["messages"].keys())
            fmt_str = "**`{index}.`** {member} \N{EM DASH} **{stars}** \N{WHITE MEDIUM STAR}"

            def fmt_(dct: dict):
                return "\n".join(
                    [
                        fmt_str.format(
                            index=index(list(dct.keys()), x), member=x.mention, stars=format_int(y)
                        )
                        for x, y in dct.items()
                    ]
                )

            given, received = (fmt_(data["given"]), fmt_(data["received"]))

            messages = slice_dict(data["messages"])
            fmt_str = "**`{index}.`** {member} \N{EM DASH} **{messages}**"
            messages = [
                "\n".join(
                    [
                        fmt_str.format(
                            index=index(msg_keys, k), member=k.mention, messages=format_int(v)
                        )
                        for k, v in x.items()
                    ]
                )
                for x in messages
            ]
            embed = discord.Embed(colour=ctx.me.colour)
            embed.set_author(name=i18n("Leaderboard"), icon_url=ctx.guild.icon_url)
            embed.add_field(name=i18n("Stars Given"), value=given or default_str)
            embed.add_field(name=i18n("Stars Received"), value=received or default_str)

            embed.add_field(
                name="\N{ZERO WIDTH JOINER}", value="\N{ZERO WIDTH JOINER}", inline=False
            )
            embed.add_field(name=i18n("Starboard Messages"), value=messages[0] or default_str)
            embed.add_field(
                name="\N{ZERO WIDTH JOINER}", value=messages[1] or "\N{ZERO WIDTH JOINER}"
            )

            await ctx.send(embed=embed)

        else:

            def fmt_(dct: dict):
                return tabulate(
                    [(str(x[0]), format_int(x[1])) for x in dct.items()], tablefmt="psql"
                )

            format_args = {
                "headers": [
                    i18n("Stars Given").center(30),
                    i18n("Stars Received").center(30),
                    i18n("Starboard Messages").center(30),
                ],
                "tables": [fmt_(data["given"]), fmt_(data["received"]), fmt_(data["messages"])],
                "divider": "\n\n{}\n\n".format("\N{EM DASH}" * 30),
            }

            message = (
                "{headers[0]}\n\n{tables[0]}{divider}{headers[1]}\n\n{tables[1]}"
                "{divider}{headers[2]}\n\n{tables[2]}"
            ).format(
                **format_args
            )
            await ctx.send_interactive(pagify(message, delims=["\n"]), box_lang="")

    ####################
    #   [p]stars

    async def ignore(
        self,
        ctx: RedContext,
        obj: Union[discord.Member, discord.TextChannel],
        *,
        modlog_case: bool = False,
        reason: str = None,
        unignore: bool = False,
    ):
        if isinstance(obj, discord.Member):
            if obj.bot:
                await ctx.send(
                    warning(
                        i18n(
                            "Bot accounts are always blocked from using the starboard, "
                            "and cannot be manually blocked nor unblocked."
                        )
                    )
                )
                return
            elif not await hierarchy_allows(self.bot, ctx.author, obj):
                await ctx.send(error(i18n("You aren't allowed to block that member")))
                return
        starboard = get_starboard(obj.guild)  # type: StarboardGuild
        if await starboard.is_ignored(obj):
            await ctx.send(
                warning(
                    i18n("That user is already blocked from using this server's starboard")
                    if isinstance(obj, discord.Member)
                    else i18n("That channel is already being ignored")
                )
            )
            return
        if await getattr(starboard, "unignore" if unignore else "ignore")(obj):
            await ctx.send(
                tick(
                    i18n("**{}** is now blocked from this server's starboard")
                    if unignore is False
                    else i18n("**{}** is no longer blocked from this server's starboard")
                ).format(
                    obj
                )
            )
            if isinstance(obj, discord.Member) and modlog_case:
                try:
                    await modlog.create_case(
                        self.bot,
                        ctx.guild,
                        ctx.message.created_at,
                        "starboardblock" if not unignore else "starboardunblock",
                        obj,
                        ctx.author,
                        reason,
                        until=None,
                        channel=None,
                    )
                except RuntimeError:
                    pass

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
        starboard = get_starboard(ctx.guild)  # type: StarboardGuild
        star = await starboard.get_message(message_id=message_id)
        if not star:
            await ctx.send(
                error(
                    i18n(
                        "That message either hasn't been starred by anyone yet, or it doesn't exist"
                    )
                )
            )
            return
        if star.hidden:
            await ctx.send(error(i18n("That message is already hidden")))
        else:
            star.hidden = True
            await ctx.send(
                tick(i18n("The message sent by **{}** is now hidden.").format(star.message.author))
            )

    @stars.command(name="unhide")
    async def stars_unhide(self, ctx: RedContext, message_id: int):
        """Unhide a previously hidden message"""
        starboard = get_starboard(ctx.guild)  # type: StarboardGuild
        star = await starboard.get_message(message_id=message_id)
        if not star:
            await ctx.send(
                error(
                    i18n(
                        "That message either hasn't been starred by anyone yet, or it doesn't exist"
                    )
                )
            )
            return
        if star.hidden is False:
            await ctx.send(error(i18n("That message hasn't been hidden")))
        else:
            star.hidden = False
            await ctx.send(
                tick(
                    i18n("The message sent by **{}** is no longer hidden.").format(
                        star.message.author
                    )
                )
            )

    @stars.command(name="block", aliases=["blacklist"])
    async def stars_block(self, ctx: RedContext, member: discord.Member, *, reason: str = None):
        """Block the passed user from using this guild's starboard

        Bot accounts are always blocked from using the starboard, and cannot be manually blocked.

        For ignoring a channel from the starboard, see `[p]starboard ignore`"""
        await self.ignore(ctx, member, reason=reason, modlog_case=True)

    @stars.command(name="unblock", aliases=["unblacklist"])
    async def stars_unblock(self, ctx: RedContext, member: discord.Member, *, reason: str = None):
        """Unblocks the passed user from using this guild's starboard

        Bot accounts are always blocked from using the starboard, and cannot be manually unblocked.

        For unignoring a channel from the starboard, see `[p]starboard unignore`"""
        await self.ignore(ctx, member, reason=reason, modlog_case=True, unignore=True)

    @stars.command(name="update")
    async def stars_update(self, ctx: RedContext, message_id: int):
        """Forcefully update a starboard message

        `message_id` should be the corresponding message that the starboard message
        is for, and not the starboard message itself."""
        starboard = get_starboard(ctx.guild)  # type: StarboardGuild
        star = await starboard.get_message(message_id=message_id)
        if star is None:
            await ctx.send(
                warning(
                    i18n("I couldn't find a message with that ID - has the message been deleted?")
                )
            )
            return
        await star.update_cached_message()
        await star.update_starboard_message()
        await ctx.send(
            tick(
                i18n(
                    "The starboard message for the message sent by **{}** has been updated"
                ).format(
                    star.author
                )
            )
        )

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
        disclaimer = i18n(
            "Are you sure you want to import your v2 instances data?\n\n"
            "Guild settings will not be imported and must be setup again.\n\n"
            "Any messages starred previous to this import that are also present "
            "in the v2 data **will be overwritten.**\n\n"
            "Please click \N{WHITE HEAVY CHECK MARK} if you wish to continue."
        )
        disclaimer = discord.Embed(
            description=disclaimer, colour=discord.Colour.gold(), title=i18n("V2 Data Import")
        )

        async with ConfirmMenu(ctx, embed=disclaimer) as result:
            if not result:
                await ctx.send(i18n("Import cancelled."), delete_after=30)
                return
            tmp = await ctx.send(i18n("Importing data... (this could take a while)"))
            try:
                async with ctx.typing():
                    await v2_import(self.bot, mongo_uri)
            except NoMotorException:
                await tmp.delete()
                await fmt(
                    ctx,
                    error(
                        i18n(
                            "Motor is not installed; cannot import v2 data.\n\n"
                            "Please use `{prefix}pipinstall motor` and restart your bot, "
                            "and re-attempt the import."
                        )
                    ),
                )
            else:
                await tmp.delete()
                await ctx.send(tick(i18n("Successfully imported v2 data")))

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
        starboard = get_starboard(ctx.guild)  # type: StarboardGuild

        ignores = {x: len(y) for x, y in (await starboard.ignored()).items()}

        await ctx.send_interactive(
            pagify(
                tabulate(
                    [
                        [
                            i18n("Starboard Channel"),
                            getattr(await starboard.get_channel(), "name", i18n("No channel set")),
                        ],
                        [i18n("Min stars"), await starboard.min_stars()],
                        [i18n("Ignored Channels"), ignores.get("channels", 0)],
                        [i18n("Ignored Members"), ignores.get("members", 0)],
                        [
                            i18n("Self-starring"),
                            i18n("Enabled") if await starboard.selfstar() else i18n("Disabled"),
                        ],
                        [i18n("Messages cached"), len(starboard.message_cache)],
                    ],
                    tablefmt="psql",
                )
            ),
            box_lang="",
        )

    @cmd_starboard.command(name="selfstar")
    async def starboard_selfstar(self, ctx: RedContext, toggle: bool = None):
        """Toggles if members can star their own messages

        Member statistics do not respect this setting, and always ignore self-stars
        when totaling stars given/received.
        """
        starboard = get_starboard(ctx.guild)  # type: StarboardGuild
        toggle = (not await starboard.selfstar()) if toggle is None else toggle
        await starboard.selfstar.set(toggle)
        await ctx.send(
            tick(
                i18n("Members can now star their own messages")
                if toggle
                else i18n("Members can no longer star their own messages")
            )
        )

    @cmd_starboard.command(name="channel")
    async def starboard_channel(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set or clear the server's starboard channel"""
        if channel and channel.guild.id != ctx.guild.id:
            await ctx.send(error(i18n("That channel isn't in this server")))
            return
        starboard = get_starboard(ctx.guild)  # type: StarboardGuild
        await starboard.channel.set(getattr(channel, "id", None))
        # starboard.channel = channel
        if channel is None:
            await ctx.send(tick(i18n("Cleared the current starboard channel")))
        else:
            await ctx.send(tick(i18n("Set the starboard channel to {}").format(channel.mention)))

    @cmd_starboard.command(name="minstars", aliases=["stars"])
    async def starboard_minstars(self, ctx: RedContext, stars: int):
        """Set the amount of stars required for a message to be sent to this guild's starboard"""
        if stars < 1:
            await ctx.send(warning(i18n("The amount of stars must be a non-zero number")))
            return
        if stars > len(list(filter(lambda x: not x.bot, ctx.guild.members))):
            await ctx.send(
                warning(
                    i18n("There aren't enough members in this server to reach that amount of stars")
                )
            )
            return
        starboard = get_starboard(ctx.guild)  # type: StarboardGuild
        await starboard.min_stars.set(stars)
        await ctx.tick()

    @cmd_starboard.command(name="ignore")
    async def starboard_ignore(self, ctx: RedContext, *, channel: discord.TextChannel):
        """Ignore a channel, preventing any stars from occurring in it

        For ignoring a member from the starboard, see `[p]stars block`"""
        await self.ignore(ctx, channel)

    @cmd_starboard.command(name="unignore")
    async def starboard_unignore(self, ctx: RedContext, *, channel: discord.TextChannel):
        """Unignore a channel, allowing stars to occur

        For unignoring a member from the starboard, see `[p]stars unblock`"""
        await self.ignore(ctx, channel, unignore=True)

    @cmd_starboard.command(name="restart_janitor", hidden=True)
    @commands.cooldown(1, 3 * 60, commands.BucketType.guild)
    async def starboard_restart_janitor(self, ctx: RedContext):
        """Restart the current server's janitor task

        This can be useful if the current server's janitor erroneously exited,
        and the root janitor task hasn't restarted it yet.

        This command can only be used once every 3 minutes per server.
        """
        starboard = get_starboard(ctx.guild)
        await starboard.setup_janitor(overwrite=True)
        await ctx.tick()

    ##################################################################################
    #   Init tasks

    async def _init_janitors(self):
        """Guild janitor management task"""
        await self.bot.wait_until_ready()
        try:
            while True:
                for guild in self.bot.guilds:
                    starboard = get_starboard(guild)
                    await starboard.setup_janitor(overwrite=False)
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
            await modlog.register_casetypes(
                [
                    {
                        "name": "starboardblock",
                        "default_setting": False,
                        "image": "\N{NO ENTRY SIGN}",
                        "case_str": "Starboard Block",
                    },
                    {
                        "name": "starboardunblock",
                        "default_setting": False,
                        "image": "\N{DOVE OF PEACE}",
                        "case_str": "Starboard Unblock",
                    },
                ]
            )
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
        await (get_starboard(guild)).setup_janitor(overwrite=False)

    # noinspection PyMethodMayBeStatic
    async def on_guild_remove(self, guild: discord.Guild):
        starboard = get_starboard(guild)
        if starboard.janitor_task:
            starboard.janitor_task.cancel()

    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        channel = self.bot.get_channel(payload.data["channel_id"])
        if isinstance(channel, (discord.abc.PrivateChannel, type(None))):
            return
        guild = channel.guild
        starboard = get_starboard(guild)  # type: StarboardGuild
        message = await starboard.get_message(message_id=payload.message_id, cache_only=True)
        if message is not None:
            await message.update_cached_message()
            message.queue_for_update()

    async def _starboard_msg(
        self, payload: RawReactionActionEvent, *, fn: str, auto_create: bool = False
    ):
        emoji = payload.emoji  # type: discord.PartialEmoji
        if not all([emoji.is_unicode_emoji(), str(emoji) == "\N{WHITE MEDIUM STAR}"]):
            return

        channel = self.bot.get_channel(payload.channel_id)  # type: discord.TextChannel
        if (
            channel is None
            or isinstance(channel, discord.abc.PrivateChannel)
            or not getattr(channel, "guild", None)
        ):
            return

        guild = channel.guild  # type: discord.Guild
        starboard = get_starboard(guild)  # type: StarboardGuild
        if await starboard.get_channel() is None:
            return

        member = guild.get_member(payload.user_id)
        if any([await starboard.is_ignored(member), await starboard.is_ignored(channel)]):
            return

        message = await starboard.get_message(
            message_id=payload.message_id, channel=channel, auto_create=auto_create
        )
        if message is None:
            return

        try:
            await getattr(message, fn)(member)
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
        starboard = get_starboard(channel.guild)  # type: StarboardGuild
        message = await starboard.get_message(message_id=payload.message_id)
        if message is None:
            return
        message.starrers = []
        message.queue_for_update()
