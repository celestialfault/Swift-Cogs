import logging
from asyncio import sleep
from random import choice
from typing import List, Tuple, Union

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import escape, pagify, warning

from cog_shared.swift_libs import FutureTime, fmt, tick, confirm

log = logging.getLogger("red.rndactivity")
_ = Translator("RNDActivity", __file__)


@cog_i18n(_)
class RNDActivity:
    """Random bot playing statuses"""

    __author__ = "odinair <odinair@odinair.xyz>"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=2042511098, force_registration=True)
        self.config.register_global(statuses=[], delay=600)
        self._status_task = self.bot.loop.create_task(self.timer())

    def __unload(self):
        self._status_task.cancel()

    @commands.group()
    @checks.is_owner()
    async def rndactivity(self, ctx: commands.Context):
        """Manage random statuses

        Available status string placeholders:

        **{GUILDS}**  Replaced with the amount of guilds the bot is in
        **{MEMBERS}**  Replaced with the amount of members in all guilds the bot is in
        **{USERS}**  Replaced with the amount of unique users the bot can see
        **{CHANNELS}**  Replaced with the total amount of channels in all guilds the bot is in
        **{SHARD}**  Replaced with the bot's shard ID
        **{SHARDS}**  Replaced with the total amount of shards the bot has loaded
        **{COMMANDS}**  Replaced with the amount of commands loaded
        **{COGS}**  Replaced with the amount of cogs loaded

        The guilds that a shard contains will be used to parse a status,
        instead of every guild the bot is in.

        Any invalid placeholders will cause the status to be ignored when switching statuses
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    _min_duration = FutureTime.get_seconds("5 minutes")

    @rndactivity.command(name="delay")
    async def rndactivity_delay(
        self,
        ctx: commands.Context,
        *,
        duration: FutureTime.converter(min_duration=_min_duration, strict=True, max_duration=None)
    ):
        """Set the amount of time required to pass to change the bot's playing status

        Duration can be formatted in any of the following ways:
        • `5m`
        • `1h3.5m`
        • `5 minutes`
        • `1 hour 3.5 minutes`

        Minimum duration between changes is 5 minutes. Default delay is every 10 minutes.
        """
        await self.config.delay.set(duration.total_seconds())
        await fmt(
            ctx,
            tick(
                _(
                    "Set time between status changes to {duration}.\nThis change will take effect "
                    "after the next status change."
                )
            ),
            duration=duration.format(),
        )

    async def _add_status(self, ctx: commands.Context, game: str, *, game_type: int = 0):
        try:
            self.format_status({"type": game_type, "game": game})
        except KeyError as e:
            await fmt(
                ctx,
                warning(
                    _(
                        "Parsing that status failed \N{EM DASH} {placeholder} is not a valid "
                        "placeholder"
                    )
                ),
                placeholder=str(e),
            )
        else:
            async with self.config.statuses() as statuses:
                statuses.append({"type": game_type, "game": game})
                await fmt(ctx, tick(_("Added status **#{id}** successfully.")), id=len(statuses))

    @rndactivity.command(name="add", aliases=["playing"])
    async def rndactivity_add(self, ctx: commands.Context, *, status: str):
        """Add a playing status"""
        await self._add_status(ctx, status)

    @rndactivity.command(name="watching")
    async def rndactivity_add_watching(self, ctx: commands.Context, *, status: str):
        """Add a watching status"""
        await self._add_status(ctx, status, game_type=3)

    @rndactivity.command(name="listening")
    async def rndactivity_add_listening(self, ctx: commands.Context, *, status: str):
        """Add a listening status"""
        await self._add_status(ctx, status, game_type=2)

    @rndactivity.command(name="parse")
    async def rndactivity_parse(self, ctx: commands.Context, *, status: str):
        """Attempt to parse a given status string"""
        shard = getattr(ctx.guild, "shard_id", 0)

        try:
            result, result_type = self.format_status(status, shard=shard)
        except KeyError as e:
            await fmt(
                ctx,
                warning(
                    _(
                        "Placeholder {placeholder} does not exist\n\n"
                        "See `{prefix}help rndactivity add` for the list of placeholder strings"
                    )
                ),
                placeholder=escape(str(e), mass_mentions=True),
            )
        else:
            await fmt(
                ctx,
                _("\N{INBOX TRAY} **Input:**\n{input}\n\N{OUTBOX TRAY} **Result:** {result}"),
                input=escape(status, mass_mentions=True),
                result=escape(result, mass_mentions=True),
            )

    @rndactivity.command(name="remove", aliases=["delete"])
    async def rndactivity_remove(self, ctx: commands.Context, status: int):
        """Remove one or more statuses by their IDs

        You can retrieve the ID for a status with [p]rndactivity list
        """
        async with self.config.statuses() as statuses:
            if len(statuses) < status:
                return await fmt(ctx, warning(_("No status with the ID `{id}` exists")), id=status)
            removed = statuses.pop(status - 1)
            if not statuses:
                await self.bot.change_presence(
                    activity=None, status=getattr(ctx.me, "status", None)
                )
        removed = escape(self.format_status(removed, return_formatted=False)[0], mass_mentions=True)
        await fmt(
            ctx,
            tick(_("Removed status **#{id}** (`{status}`) successfully.")),
            id=status,
            status=removed,
        )

    @rndactivity.command(name="list")
    async def rndactivity_list(self, ctx: commands.Context, parse: bool = False):
        """Lists all set statuses

        If parse is passed, all status strings are shown as their parsed output,
        similarly to `[p]rndactivity parse`. Invalid placeholders will still be identified and
        marked without enabling parse mode
        """
        orig_statuses = list(await self.config.statuses())
        if not orig_statuses:
            return await fmt(
                ctx,
                warning(
                    _("I have no statuses setup yet! " "Use `{prefix}rndactivity add` to add some!")
                ),
            )
        statuses = []
        shard = getattr(ctx.guild, "shard_id", 0)
        for item in orig_statuses:
            try:
                parsed, game_type = self.format_status(item, shard=shard, return_formatted=parse)
                statuses.append("{} \N{EM DASH} {!r}".format(orig_statuses.index(item) + 1, parsed))
            except KeyError as e:
                if isinstance(item, str):
                    status = item
                else:
                    status = item["game"]
                statuses.append(
                    "{} \N{EM DASH} {!r}  # {}".format(
                        orig_statuses.index(item) + 1,
                        status,
                        _("Placeholder {} doesn't exist").format(str(e)),
                    )
                )

        await ctx.send_interactive(
            messages=pagify("\n".join(statuses), escape_mass_mentions=True, shorten_by=10),
            box_lang="py",
        )

    @rndactivity.command(name="clear")
    async def rndactivity_clear(self, ctx: commands.Context):
        """Clears all set statuses"""
        amount = len(await self.config.statuses())
        if await confirm(
            ctx,
            content=_(
                "Are you sure you want to clear {amount} statuses?\n\n"
                "**This action is irreversible!**"
            ).format(amount=amount),
        ):
            await self.config.statuses.set([])
            await self.bot.change_presence(activity=None, status=self.bot.guilds[0].me.status)
            await fmt(ctx, tick(_("Successfully removed {amount} status strings.")), amount=amount)
        else:
            await fmt(ctx, _("Okay then."))

    def format_status(
        self, status: Union[str, dict], shard: int = 0, return_formatted=True
    ) -> Union[str, Tuple[str, int]]:
        game_type = 0
        if isinstance(status, dict):
            game_type: int = status.get("type", 0)
            status: str = status.get("game")
        formatted = status.format(
            GUILDS=len(self.bot.guilds),
            SHARDS=self.bot.shard_count,
            SHARD=shard + 1,
            COGS=len(self.bot.cogs),
            COMMANDS=len(self.bot.all_commands),
            MEMBERS=sum([x.member_count for x in self.bot.guilds]),
            UNIQUE_MEMBERS=len(self.bot.users),
            USERS=len(self.bot.users),
            CHANNELS=sum([len(x.channels) for x in self.bot.guilds]),
        )
        return status if not return_formatted else formatted, game_type

    async def update_status(self, statuses: List[str]):
        if not statuses:
            return
        status = choice(statuses)
        for shard in self.bot.shards.keys():
            try:
                game, game_type = self.format_status(status, shard=shard)
            except KeyError as e:
                log.warning(
                    "Encountered invalid placeholder {!s} while attempting to parse status "
                    "#{}, skipping status update.".format(e, statuses.index(status) + 1)
                )
                return
            game = discord.Activity(name=game, type=discord.ActivityType(game_type))
            await self.bot.change_presence(
                activity=game, status=self.bot.guilds[0].me.status, shard_id=shard
            )

    async def timer(self):
        await self.bot.wait_until_ready()
        while True:
            await self.update_status(list(await self.config.statuses()))
            await sleep(int(await self.config.delay()))
