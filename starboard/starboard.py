import asyncio
import contextlib
import json
from typing import Tuple

import discord
from discord.raw_models import RawMessageUpdateEvent, RawReactionActionEvent, RawReactionClearEvent
from redbot.core import Config, checks, commands, modlog
from redbot.core.bot import Red
from redbot.core.i18n import cog_i18n
from redbot.core.utils.chat_formatting import bold, box, error, info, inline, pagify, warning

from cog_shared.swift_libs import cmd_help, confirm, fmt, hierarchy_allows, index, resolve_any, tick
from starboard import stats, v2_migration
from starboard.base import StarboardBase, get_starboard, get_starboard_cache
from starboard.checks import can_use_starboard
from starboard.exceptions import BlockedException, SelfStarException, StarboardException
from starboard.guild import StarboardGuild
from starboard.shared import log, i18n
from starboard.message import AutoStarboardMessage, StarboardMessage

medals = ["\N{FIRST PLACE MEDAL}", "\N{SECOND PLACE MEDAL}", "\N{THIRD PLACE MEDAL}", "**`{}.`**"]


class Context(commands.Context):
    """Type hints class for __before_invoke command hooks"""
    starboard: StarboardGuild = None


@cog_i18n(i18n)
class Starboard(StarboardBase):
    """It's almost like pinning messages, except with stars"""

    __author__ = "odinair <odinair@odinair.xyz>"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=45351212589, force_registration=True)
        self.config.register_guild(
            **{
                "ignored": {"members": [], "channels": []},
                "channel": None,
                "min_stars": 1,
                "selfstar": True,
            }
        )

        self._tasks: Tuple[asyncio.Task, ...] = (
            self.bot.loop.create_task(self._register_cases()),
            self.bot.loop.create_task(self._init_janitors()),
        )

    # noinspection PyMethodMayBeStatic
    async def __before_invoke(self, ctx: Context):
        # inject some commonly retrieved data to the context object we're given
        ctx.starboard = get_starboard(ctx.guild) if ctx.guild else None

    # noinspection PyMethodMayBeStatic
    async def __after_invoke(self, ctx: Context):
        # and try to clean up after ourselves when we're done
        with contextlib.suppress(AttributeError):
            delattr(ctx, "starboard")

    ####################
    #   [p]star

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @can_use_starboard()
    async def star(self, ctx: Context, message: AutoStarboardMessage):
        """Star a message by it's ID"""
        if message.has_starred(ctx.author):
            await ctx.send(
                warning(
                    i18n(
                        "You've already starred that message\n\n"
                        "(you can use `{}star remove` to remove your star)"
                    ).format(ctx.prefix)
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
    async def star_show(self, ctx: Context, message: StarboardMessage):
        """Show the starboard message for the message given"""
        if not message.stars:
            raise commands.BadArgument
        await ctx.send(**message.starboard_message_contents)

    @star.command(name="remove", aliases=["rm"])
    async def star_remove(self, ctx: Context, message: StarboardMessage):
        """Remove a previously added star"""
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
    async def star_stats(self, ctx: Context, *, member: discord.Member = None):
        """Get your or a specified member's stats"""
        member = member or ctx.author
        data = {k: f"{v:,}" for k, v in (await stats.user_stats(member)).items()}
        await ctx.send(
            info(
                i18n(
                    "{member} has given **{given}** star(s), received **{received}**"
                    " star(s) with a max of **{max_received}** star(s) on a single message,"
                    " and have **{messages}** total message(s) on this server's starboard."
                ).format(member=bold(str(member)), **data)
            )
        )

    @star.command(name="leaderboard", aliases=["lb"])
    async def star_leaderboard(self, ctx: Context):
        """Retrieve the star leaderboard for the current server"""
        data = await stats.leaderboard(ctx.guild, top=8)

        def fmt_data(dct: dict, emoji: str = "\N{WHITE MEDIUM STAR}"):
            items = []
            keys = list(dct.keys())
            for x, y in dct.items():
                medal = medals[min(len(medals) - 1, keys.index(x))].format(index(keys, x))
                items.append(f"{medal} {x.mention} \N{EM DASH} **{y:,}** {emoji}")
            return "\n".join(items) or inline(i18n("There's nothing here yet..."))

        await ctx.send(
            embed=(
                discord.Embed(colour=ctx.me.colour)
                .set_author(name=i18n("Server Leaderboard"), icon_url=ctx.guild.icon_url)
                .add_field(name=i18n("Stars Given"), value=fmt_data(data["given"]))
                .add_field(name=i18n("Stars Received"), value=fmt_data(data["received"]))
                .add_field(
                    name="\N{ZERO WIDTH JOINER}", value="\N{ZERO WIDTH JOINER}", inline=False
                )
                .add_field(name=i18n("Max Stars Received"), value=fmt_data(data["max_received"]))
                .add_field(
                    name=i18n("Starboard Messages"),
                    value=fmt_data(data["messages"], emoji="\N{ENVELOPE}"),
                )
            )
        )

    ####################
    #   [p]stars

    @commands.group(name="stars")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def stars(self, ctx: Context):
        """Manage starboard messages"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @stars.command(name="ignore", aliases=["block"])
    async def stars_ignore(self, ctx: Context, name: str, *, reason: str = None):
        """Add a channel or member to the server's ignore list

        `reason` is only used if ignoring a member
        """
        item = await resolve_any(ctx, name, commands.TextChannelConverter, commands.MemberConverter)

        if isinstance(item, discord.Member) and not await hierarchy_allows(
            self.bot, ctx.author, item
        ):
            await ctx.send(error(i18n("You aren't allowed to add that member to the ignore list")))
            return
        elif (
            isinstance(item, discord.TextChannel)
            and item == await ctx.starboard.resolve_starboard()
        ):
            await ctx.send(
                warning(
                    i18n(
                        "The starboard channel is always ignored and cannot be manually "
                        "ignored nor unignored."
                    )
                )
            )
            return

        if await ctx.starboard.is_ignored(item):
            await ctx.send(
                warning(
                    i18n("That user is already ignored from using this server's starboard")
                    if isinstance(item, discord.Member)
                    else i18n("That channel is already being ignored")
                )
            )
            return

        await ctx.starboard.ignore(item)
        await ctx.send(
            tick(i18n("**{}** is now ignored from this server's starboard")).format(item)
        )

        if isinstance(item, discord.Member):
            try:
                await modlog.create_case(
                    bot=self.bot,
                    guild=ctx.guild,
                    created_at=ctx.message.created_at,
                    action_type="starboardblock",
                    user=item,
                    moderator=ctx.author,
                    reason=reason,
                    until=None,
                    channel=None,
                )
            except RuntimeError:
                pass

    @stars.command(name="unignore", aliases=["unblock"])
    async def stars_unignore(self, ctx: Context, name: str, *, reason: str = None):
        """Remove a channel or member from the server's ignore list

        `reason` is only used if unignoring a member
        """
        item = await resolve_any(ctx, name, commands.TextChannelConverter, commands.MemberConverter)

        if isinstance(item, discord.Member) and not await hierarchy_allows(
            self.bot, ctx.author, item
        ):
            await ctx.send(
                error(i18n("You aren't allowed to remove that member from the ignore list"))
            )
            return
        elif (
            isinstance(item, discord.TextChannel)
            and item == await ctx.starboard.resolve_starboard()
        ):
            await ctx.send(
                warning(
                    i18n(
                        "The starboard channel is always ignored and cannot be manually "
                        "ignored nor unignored."
                    )
                )
            )
            return

        if not await ctx.starboard.is_ignored(item):
            await ctx.send(
                warning(
                    i18n("That user is not already ignored from using this server's starboard")
                    if isinstance(item, discord.Member)
                    else i18n("That channel is not already being ignored")
                )
            )
            return

        await ctx.starboard.unignore(item)
        await ctx.send(
            tick(i18n("**{}** is no longer ignored from this server's starboard")).format(item)
        )

        if isinstance(item, discord.Member):
            try:
                await modlog.create_case(
                    bot=self.bot,
                    guild=ctx.guild,
                    created_at=ctx.message.created_at,
                    action_type="starboardunblock",
                    user=item,
                    moderator=ctx.author,
                    reason=reason,
                    until=None,
                    channel=None,
                )
            except RuntimeError:
                pass

    @stars.command(name="hide")
    async def stars_hide(self, ctx: Context, message: StarboardMessage):
        """Hide a message from the starboard"""
        if message.hidden:
            return await ctx.send(error(i18n("That message is already hidden")))
        message.hidden = True
        await ctx.send(
            tick(i18n("The message sent by **{}** is now hidden.").format(message.author))
        )

    @stars.command(name="unhide")
    async def stars_unhide(self, ctx: Context, message: StarboardMessage):
        """Unhide a previously hidden message"""
        if message.hidden is False:
            return await ctx.send(error(i18n("That message hasn't been hidden")))
        message.hidden = False
        await ctx.send(
            tick(i18n("The message sent by **{}** is no longer hidden.").format(message.author))
        )

    @stars.command(name="update")
    async def stars_update(self, ctx: Context, message: StarboardMessage):
        """Forcefully update a starboard message"""
        await message.update_cached_message()
        await message.update_starboard_message()
        await ctx.send(tick(i18n("Message has been updated.")))

    ####################
    #   [p]starboardset

    @commands.group(name="starboardset")
    @checks.is_owner()
    async def starboardset(self, ctx: Context):
        """Core Starboard cog management"""
        await cmd_help(ctx)

    @starboardset.command(name="json")
    async def starboardset_json(self, ctx: Context, message_id: int, guild_id: int = None):
        """Retrieve the raw data stored for a given message"""
        guild = ctx.guild if guild_id is None else self.bot.get_guild(guild_id)
        if guild is None:
            raise commands.BadArgument

        data = await ctx.starboard.messages.get_raw(str(message_id))
        if data is None:
            raise commands.BadArgument
        await ctx.send_interactive(pagify(json.dumps(data, indent=2)), box_lang="json")

    @starboardset.command(name="v2_import")
    @commands.check(lambda ctx: not v2_migration.import_lock.locked())
    async def starboardset_v2_import(self, ctx: Context, mongo_uri: str):
        """Import Red v2 instance data

        Please note that this is not officially supported, and this import tool
        is provided as-is.

        Only messages are imported currently; server settings are not imported,
        and must be setup again.

        In most cases, `mongodb://localhost:27017` will work just fine
        if you're importing a local v2 instance.
        """
        if not await confirm(
            ctx,
            timeout=90.0,
            content=i18n(
                "**PLEASE READ THIS! UNEXPECTED BAD THINGS MAY HAPPEN IF YOU DON'T!**"
                "\n"
                "Importing from v2 instances is not officially supported, due to the vast"
                " differences in backend data storage schemas. This command is provided as-is,"
                " with no guarantee of maintenance nor stability."
                "\n\n"
                "Server settings will not be imported and must be setup again."
                "\n"
                "Starred messages data will be imported, but if a message is present in"
                " my current data set, **it will be overwritten** with the imported data."
                "\n\n\n"
                "Please react with \N{WHITE HEAVY CHECK MARK} to confirm that you wish to continue."
            ),
        ):
            await ctx.send(i18n("Import cancelled."), delete_after=30)
            return

        tmp = await ctx.send(i18n("Importing data... (this could take a while)"))
        try:
            async with ctx.typing():
                await v2_migration.import_data(self.bot, mongo_uri)
        except v2_migration.NoMotorError:
            await fmt(
                ctx,
                error(
                    i18n(
                        "Motor is not installed; cannot import v2 data.\n\n"
                        "Please do `{prefix}pipinstall motor` and re-attempt the import."
                    )
                ),
            )
        else:
            await ctx.send(tick(i18n("Imported successfully.")))
        finally:
            await tmp.delete()

    ####################
    #   [p]starboard

    @commands.group(name="starboard")
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def cmd_starboard(self, ctx: Context):
        """Manage the server starboard"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()
            await ctx.send(
                box(
                    i18n(
                        "Starboard channel: {channel}\n"
                        "Min stars: {min_stars}\n"
                        "Cached messages: {cache_len}"
                    ).format(
                        channel=await ctx.starboard.resolve_starboard() or i18n("No channel setup"),
                        min_stars=await ctx.starboard.min_stars(),
                        cache_len=len(ctx.starboard.message_cache),
                    )
                )
            )

    @cmd_starboard.command(name="selfstar")
    async def starboard_selfstar(self, ctx: Context, toggle: bool = None):
        """Toggles if members can star their own messages

        Member statistics do not respect this setting, and always ignore self-stars.
        """
        toggle = (not await ctx.starboard.selfstar()) if toggle is None else toggle
        await ctx.starboard.selfstar.set(toggle)
        await ctx.send(
            tick(
                i18n("Members can now star their own messages")
                if toggle
                else i18n("Members can no longer star their own messages")
            )
        )

    @cmd_starboard.command(name="channel")
    async def starboard_channel(self, ctx: Context, channel: discord.TextChannel = None):
        """Set or clear the server's starboard channel"""
        if channel and channel.guild.id != ctx.guild.id:
            await ctx.send(error(i18n("That channel isn't in this server")))
            return
        await ctx.starboard.channel.set(getattr(channel, "id", None))
        if channel is None:
            await ctx.send(tick(i18n("Cleared the current starboard channel")))
        else:
            await ctx.send(tick(i18n("Set the starboard channel to {}").format(channel.mention)))

    @cmd_starboard.command(name="minstars", aliases=["stars"])
    async def starboard_minstars(self, ctx: Context, stars: int):
        """Set the amount of stars required for a message to be sent to this server's starboard"""
        if stars < 1:
            await ctx.send(warning(i18n("The amount of stars must be a non-zero number")))
            return
        if stars > len([x for x in ctx.guild.members if not x.bot]):
            await ctx.send(
                warning(
                    i18n(
                        "There aren't enough members in this server to reach"
                        " the given amount of stars. Maybe try a lower number?"
                    )
                )
            )
            return
        await ctx.starboard.min_stars.set(stars)
        await ctx.tick()

    @cmd_starboard.command(name="restart_janitor", hidden=True)
    @commands.cooldown(1, 3 * 60, commands.BucketType.guild)
    @checks.guildowner_or_permissions(administrator=True)
    async def starboard_restart_janitor(self, ctx: Context):
        """Force a restart of current server's janitor task"""
        await ctx.starboard.setup_janitor(overwrite=True)
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
        # guild janitor tasks are cancelled by _init_janitors
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
        starboard: StarboardGuild = get_starboard(guild)
        message = await starboard.get_message(message_id=payload.message_id, cache_only=True)
        if message is not None:
            await message.update_cached_message()
            message.queue_for_update()

    async def _get_message(self, payload: RawReactionActionEvent, **kwargs) -> dict:
        emoji: discord.PartialEmoji = payload.emoji
        if not all([emoji.is_unicode_emoji(), str(emoji) == "\N{WHITE MEDIUM STAR}"]):
            return {}

        channel: discord.TextChannel = self.bot.get_channel(payload.channel_id)
        if (
            channel is None
            or isinstance(channel, discord.abc.PrivateChannel)
            or not getattr(channel, "guild", None)
        ):
            return {}

        guild: discord.Guild = channel.guild
        member: discord.Member = guild.get_member(payload.user_id)
        starboard: StarboardGuild = get_starboard(guild)
        if await starboard.resolve_starboard() is None:
            return {}

        return {
            "message": await starboard.get_message(
                message_id=payload.message_id, channel=channel, **kwargs
            ),
            "member": member,
            "channel": channel,
            "emoji": emoji,
        }

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        data = await self._get_message(payload, auto_create=True)
        message: StarboardMessage = data.get("message")
        member: discord.Member = data.get("member")
        emoji: discord.PartialEmoji = data.get("emoji")
        channel: discord.TextChannel = data.get("channel")
        if not message:
            return

        try:
            await message.add_star(member)
        except BlockedException:
            if channel.permissions_for(channel.guild.me).manage_messages:
                try:
                    await message.message.remove_reaction(emoji=emoji, member=member)
                except discord.HTTPException:
                    pass
        except StarboardException:
            pass

    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        data = await self._get_message(payload, auto_create=True)
        message: StarboardMessage = data.get("message")
        member: discord.Member = data.get("member")
        if not message:
            return

        try:
            await message.remove_star(member)
        except StarboardException:
            pass

    async def on_raw_reaction_clear(self, payload: RawReactionClearEvent):
        channel: discord.TextChannel = self.bot.get_channel(payload.channel_id)
        if channel is None or isinstance(channel, discord.abc.PrivateChannel):
            return
        starboard: StarboardGuild = get_starboard(channel.guild)
        message = await starboard.get_message(message_id=payload.message_id)
        if message is None:
            return
        message.starrers = []
        message.queue_for_update()
