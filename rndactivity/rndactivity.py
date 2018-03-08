from asyncio import sleep
from typing import List

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import Config, checks
from redbot.core.utils.chat_formatting import pagify, info, warning, escape

from random import choice

from odinair_libs.menus import confirm
from odinair_libs.converters import FutureTime
from odinair_libs.formatting import tick


class RNDActivity:
    """Random bot playing statuses"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=2042511098, force_registration=True)
        self.config.register_global(statuses=[], delay=600)
        self._status_task = self.bot.loop.create_task(self.timer())

    def __unload(self):
        self._status_task.cancel()

    @commands.group()
    @checks.is_owner()
    async def rndactivity(self, ctx: RedContext):
        """Manage random statuses"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    _min_duration = FutureTime.get_seconds("5 minutes")

    @rndactivity.command(name="delay")
    async def rndactivity_delay(self, ctx: RedContext, *,
                                duration: FutureTime.converter(min_duration=_min_duration, strict=True,
                                                               max_duration=None)):
        """Set the amount of time required to pass in seconds to change the bot's playing status

        Duration can be formatted like `7.5m`, `1h7.5m`, `7.5 minutes`, or `1 hour 7.5 minutes`

        Minimum duration between changes is 5 minutes.
        Default delay is 10 minutes, or every 600 seconds
        """
        await self.config.delay.set(duration.total_seconds())
        await ctx.send(tick(f"Set time between status changes to {duration.format()}.\n"
                            f"This will take effect after the next status change."))

    async def _add_status(self, ctx: RedContext, game: str, *, game_type: int = 0):
        try:
            self.format_status({"type": game_type, "game": game})
        except KeyError as e:
            await ctx.send(warning("Parsing that status failed - {0!s} is not a valid placeholder".format(e)))

        async with self.config.statuses() as statuses:
            statuses.append({"type": game_type, "game": game})
            await ctx.send(tick("Status **#{}** added.".format(len(statuses))))

    @rndactivity.command(name="add", aliases=["playing"])
    async def rndactivity_add(self, ctx: RedContext, *, status: str):
        """Add a playing status

        Available placeholders:

        **{GUILDS}**  Replaced with the amount of guilds the bot is in
        **{MEMBERS}**  Replaced with the amount of members that the bot can see in every guild
        **{SHARD}**  Replaced with the bot's shard ID
        **{SHARDS}**  Replaced with the total amount of shards the bot has loaded
        **{COMMANDS}**  Replaced with the amount of commands loaded
        **{COGS}**  Replaced with the amount of cogs loaded

        The guilds that a shard contains will be used to parse a status, instead of every guild the bot is in.

        You can use `[p]rndactivity parse` to test your status strings

        Any invalid placeholders will cause the status to be ignored when switching statuses
        """
        await self._add_status(ctx, status)

    @rndactivity.command(name="watching")
    async def rndactivity_add_watching(self, ctx: RedContext, *, status: str):
        """Add a watching status

        See `[p]help rndactivity add` for help on placeholders
        """
        await self._add_status(ctx, status, game_type=3)

    @rndactivity.command(name="listening")
    async def rndactivity_add_listening(self, ctx: RedContext, *, status: str):
        """Add a listening status

        See `[p]help rndactivity add` for help on placeholders
        """
        await self._add_status(ctx, status, game_type=2)

    @rndactivity.command(name="parse")
    async def rndactivity_parse(self, ctx: RedContext, *, status: str):
        """Attempt to parse a given status string

        See `[p]help rndactivity add` for the list of available placeholders
        """
        shard = getattr(ctx.guild, "shard_id", 0)

        try:
            result, result_type, _ = self.format_status(status, shard=shard)
        except KeyError as e:
            await ctx.send(warning(f"Placeholder {escape(str(e), mass_mentions=True)} does not exist\n\n"
                                   f"See `{ctx.prefix}help rndactivity add` for the list of placeholder strings"))
            return

        status = escape(status, mass_mentions=True)
        result = escape(result.format(SHARD=shard + 1), mass_mentions=True)
        await ctx.send(content=f"\N{INBOX TRAY} **Input:**\n{status}\n\n"
                               f"\N{OUTBOX TRAY} **Result:**\n{result}")

    @rndactivity.command(name="remove", aliases=["delete"])
    async def rndactivity_remove(self, ctx: RedContext, *statuses: int):
        """Remove one or more statuses by their IDs

        You can retrieve the ID for a status with [p]rndactivity list
        """
        statuses = [x for x in statuses if x > 0]
        if not statuses:
            await ctx.send_help()
            return

        bot_statuses = list(await self.config.statuses())
        for status in statuses:
            if len(bot_statuses) < status:
                await ctx.send(warning(f"The status {status} doesn't exist"))
                return
            bot_statuses[status - 1] = None

        bot_statuses = [x for x in bot_statuses if x is not None]  # Clear out None entries
        await self.config.statuses.set(bot_statuses)
        if len(bot_statuses) == 0:
            await self.bot.change_presence(game=None, status=self.bot.guilds[0].me.status)
        await ctx.send(info(f"Removed {len(statuses)} status{'es' if len(statuses) != 1 else ''}."))

    @rndactivity.command(name="list")
    async def rndactivity_list(self, ctx: RedContext, parse: bool=False):
        """Lists all set statuses

        If parse is passed, all status strings are shown as their parsed output, similarly to `[p]rndactivity parse`
        Invalid placeholders will still be identified and marked without enabling parse mode
        """
        orig_statuses = list(await self.config.statuses())
        if not len(orig_statuses):
            await ctx.send(warning(f"I have no random statuses setup! Use `{ctx.prefix}rndactivity add` to add some!"))
            return
        statuses = []
        shard = getattr(ctx.guild, "shard_id", 0)
        for item in orig_statuses:
            try:
                parsed, game_type, _ = self.format_status(item, shard=shard, return_formatted=parse)
                statuses.append(parsed if not parse else parsed.format(SHARD=shard + 1))
            except KeyError as e:
                statuses.append("{0} [placeholder {1!s} does not exist]".format(item, e))

        await ctx.send_interactive(
            messages=pagify("\n".join([f"{statuses.index(x) + 1} \N{EM DASH} {x!r}" for x in statuses]),
                            escape_mass_mentions=True, shorten_by=10),
            box_lang="py")

    @rndactivity.command(name="clear")
    async def rndactivity_clear(self, ctx: RedContext):
        """Clears all set statuses"""
        amnt = len(await self.config.statuses())
        if await confirm(ctx, f"Are you sure you want to clear {amnt} statuses?\n\nThis action is irreversible!",
                         colour=discord.Colour.red()):
            await self.config.statuses.set([])
            await self.bot.change_presence(game=None, status=self.bot.guilds[0].me.status)
            await ctx.send(tick(f"Successfully cleared {amnt} status strings."), delete_after=15.0)
        else:
            await ctx.send("Okay then.", delete_after=15.0)

    def format_status(self, status: str or dict, shard: int = None, return_formatted=True):
        game_type = 0
        if isinstance(status, dict):
            game_type = status.get("type", 0)
            status = status.get("game")
        guilds = self.bot.guilds
        if shard is not None:
            guilds = [x for x in guilds if x.shard_id == shard]
        if return_formatted:
            status = status.format(
                GUILDS=len(guilds),
                SHARDS=self.bot.shard_count,
                COGS=len(self.bot.cogs),
                COMMANDS=len(self.bot.all_commands),
                MEMBERS=sum([x.member_count for x in guilds]),
                # the following placeholder is a no-op for update_status / [p]rndactivity list|parse
                # if this isn't present, any status strings with it will throw a KeyError despite it being valid
                SHARD="{SHARD}" if shard is None else shard + 1
            )
        return status, game_type, guilds

    async def update_status(self, statuses: List[str]):
        if not statuses:
            return
        status = choice(statuses)
        for shard in self.bot.shards.keys():
            try:
                game, game_type, guilds = self.format_status(status, shard=shard)
            except KeyError:
                return
            game = discord.Activity(name=game.format(SHARD=shard + 1), type=discord.ActivityType(game_type))
            await self.bot.change_presence(activity=game, status=guilds[0].me.status, shard_id=shard)

    async def timer(self):
        while self == self.bot.get_cog(self.__class__.__name__):
            await self.update_status(list(await self.config.statuses()))
            await sleep(int(await self.config.delay()))
