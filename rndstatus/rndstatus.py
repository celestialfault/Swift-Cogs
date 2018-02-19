from asyncio import sleep
from typing import List

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import Config, checks
from redbot.core.utils.chat_formatting import error, pagify, info, warning, box

from random import choice, randint

from odinair_libs.menus import confirm
from odinair_libs.converters import FutureTime
from odinair_libs.formatting import td_format, tick


class RNDStatus:
    """Random bot playing statuses"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=2042511098, force_registration=True)
        self.config.register_global(statuses=[], delay=600)
        self._status_task = self.bot.loop.create_task(self.timer())

    def __unload(self):
        self._status_task.cancel()

    @commands.group(name="rndstatus")
    @checks.is_owner()
    async def rndstatus(self, ctx: RedContext):
        """Manage random statuses"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    _min_duration = FutureTime.get_seconds("5 minutes")

    @rndstatus.command(name="delay")
    async def rndstatus_delay(self, ctx: RedContext, *,
                              duration: FutureTime(min_duration=_min_duration, strict=True, max_duration=None)):
        """Set the amount of time required to pass in seconds to change the bot's playing status

        Duration can be formatted like `7.5m`, `1h7.5m`, `7.5 minutes`, or `1 hour 7.5 minutes`

        Minimum duration between changes is 5 minutes
        Default delay is every 10 minutes, or every 600 seconds
        """
        await self.config.delay.set(duration.total_seconds())
        await ctx.send(tick("Set time between status changes to {}.\n"
                            "This will take effect after the next status change."
                            "".format(td_format(duration))))

    async def _add_status(self, ctx: RedContext, game: str, game_type: int=0):
        try:
            self.format_status({"type": game_type, "game": game})
        except KeyError as e:
            await ctx.send(warning("Parsing that status failed - {0!s} is not a valid placeholder".format(e)))

        async with self.config.statuses() as statuses:
            statuses.append({"type": game_type, "game": game})
            await ctx.send(tick("Status **#{}** added.".format(len(statuses))))

    @rndstatus.command(name="add")
    async def rndstatus_add(self, ctx: RedContext, *, status: str):
        """Add a playing status

        Available placeholders:

        **{GUILDS}**  Replaced with the amount of guilds the bot is in
        **{MEMBERS}**  Replaced with the amount of members that the bot can see in every guild
        **{SHARD}**  Replaced with the bot's shard ID
        **{SHARDS}**  Replaced with the total amount of shards the bot has loaded
        **{COMMANDS}**  Replaced with the amount of commands loaded
        **{COGS}**  Replaced with the amount of cogs loaded

        The guilds that a shard contains will be used to parse a status, instead of every guild the bot is in.

        You can use `[p]rndstatus parse` to test your status strings

        Any invalid placeholders will cause the status to be ignored when switching statuses
        """
        await self._add_status(ctx, status)

    @rndstatus.command(name="watching")
    async def rndstatus_add_watching(self, ctx: RedContext, *, status: str):
        """Add a watching status

        See `[p]help rndstatus add` for help on placeholders
        """
        await self._add_status(ctx, status, 3)

    @rndstatus.command(name="listening")
    async def rndstatus_add_listening(self, ctx: RedContext, *, status: str):
        """Add a listening status

        See `[p]help rndstatus add` for help on placeholders
        """
        await self._add_status(ctx, status, 2)

    @rndstatus.command(name="parse")
    async def rndstatus_parse(self, ctx: RedContext, *, status: str):
        """Attempt to parse a given status string

        See `[p]help rndstatus add` for the list of available placeholders

        **NOTE:** The shard placeholder will return a random shard number if this command is ran in direct messages,
        otherwise the shard ID for the guild this command is ran in will be used
        """
        shard = randint(1, self.bot.shard_count) if ctx.guild is None else ctx.guild.shard_id + 1
        try:
            result, _ = self.format_status(status, shard=shard)
        except KeyError as e:
            await ctx.send(warning("Placeholder {0!s} does not exist\n\nSee `{1}help rndstatus add` for the list"
                                   " of replacement strings".format(e, ctx.prefix)))
            return
        msg = info("Input:\n{}\n".format(box(status)))
        msg += info("Result:\n{}".format(box(result.format(SHARD=shard))))
        await ctx.send(msg)

    @rndstatus.command(name="remove", aliases=["delete"])
    async def rndstatus_remove(self, ctx: RedContext, *statuses: int):
        """Remove one or more statuses by their IDs

        You can retrieve the ID for a status with [p]rndstatus list
        """
        statuses = [x for x in statuses if x > 0]
        if not statuses:
            await ctx.send_help()
            return

        bot_statuses = list(await self.config.statuses())
        for status in statuses:
            if len(bot_statuses) < status:
                await ctx.send(error("The status {} doesn't exist".format(status)))
                return
            bot_statuses[status - 1] = None

        bot_statuses = [x for x in bot_statuses if x is not None]  # Clear out None entries
        await self.config.statuses.set(bot_statuses)
        if len(bot_statuses) == 0:
            await self.bot.change_presence(game=None, status=self.bot.guilds[0].me.status)
        await ctx.send(info("Removed {} status{} successfully".format(len(statuses),
                                                                      "es" if len(statuses) > 1 else "")))

    @rndstatus.command(name="list")
    async def rndstatus_list(self, ctx: RedContext, parse: bool=False):
        """Lists all set statuses

        If parse is passed, all status strings are shown as their parsed output, similarly to `[p]rndstatus parse`
        Invalid placeholders will still be identified and marked without enabling parse mode
        """
        orig_statuses = list(await self.config.statuses())
        if not len(orig_statuses):
            await ctx.send(warning("I have no random statuses setup! Use `{}rndstatus add` to add some!"
                                   .format(ctx.prefix)))
            return
        statuses = []
        shard = randint(1, self.bot.shard_count) if getattr(ctx, "guild", None) is None else ctx.guild.shard_id + 1
        for item in orig_statuses:
            try:
                parsed, game_type = self.format_status(item, shard=shard, return_formatted=parse)
                statuses.append(parsed if not parse else parsed.format(SHARD=shard))
            except KeyError as e:
                statuses.append("{0} [placeholder {1!s} does not exist]".format(item, e))
        status_list = ["[{}] {}".format(statuses.index(x) + 1, x) for x in statuses]
        await ctx.send_interactive(messages=pagify("\n".join(status_list), delims=["\n"], escape_mass_mentions=True,
                                                   page_length=1990), box_lang="ini")

    @rndstatus.command(name="clear")
    async def rndstatus_clear(self, ctx: RedContext):
        """Clears all set statuses"""
        curr = len(await self.config.statuses())
        if await confirm(ctx,
                         "Are you sure you want to clear {} statuses?\n\nThis action is irreversible!".format(curr),
                         colour=discord.Colour.red()):
            await self.config.statuses.set([])
            await ctx.send("\N{WHITE HEAVY CHECK MARK} Successfully cleared {} status strings.".format(curr),
                           delete_after=15.0)
        else:
            await ctx.send("Okay then.", delete_after=15.0)

    def format_status(self, status: str or dict, shard: int = None, return_formatted=True):
        game_type = 0
        if isinstance(status, dict):
            game_type = status.get("type", 0)
            status = status["game"]
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
                # the following placeholder is a no-op for update_status / [p]rndstatus list|parse
                # if this isn't present, any status strings with it will throw a KeyError despite it being valid
                SHARD="{SHARD}"
            )
        return status, game_type

    async def update_status(self, statuses: List[str]):
        if not statuses:
            return
        status = choice(statuses)
        for shard in self.bot.shards.keys():
            try:
                game, game_type = self.format_status(status, shard=shard)
            except KeyError:
                return
            game = discord.Game(name=game.format(SHARD=shard + 1), type=game_type)
            await self.bot.change_presence(game=game, status=self.bot.guilds[0].me.status,
                                           # Individually set the status of each shard
                                           # Doing this enables the possibility of the {SHARD} placeholder
                                           shard_id=shard)

    async def timer(self):
        while self == self.bot.get_cog(self.__class__.__name__):
            await self.update_status(list(await self.config.statuses()))
            await sleep(int(await self.config.delay()))
