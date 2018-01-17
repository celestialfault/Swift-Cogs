import asyncio
from typing import List

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import Config, checks
from redbot.core.utils.chat_formatting import error, pagify, info, warning, box

from random import choice, randint


class RNDStatus:
    """Random bot playing statuses"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=2042511098, force_registration=True)
        self.config.register_global(statuses=[], delay=300)
        self.bot.loop.create_task(self.timer())

    @commands.group(name="rndstatus")
    @checks.is_owner()
    async def rndstatus(self, ctx: RedContext):
        """Manage random statuses"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @rndstatus.command(name="delay")
    async def rndstatus_delay(self, ctx: RedContext, seconds: int):
        """Set the amount of time required to pass in seconds to change the bot's playing status

        Minimum amount of seconds between changes is 60
        Default delay is every 5 minutes, or every 300 seconds"""
        if seconds < 60:
            await ctx.send_help()
            return
        await self.config.delay.set(seconds)
        await ctx.tick()

    @rndstatus.command(name="add")
    async def rndstatus_add(self, ctx: RedContext, *, status: str):
        """Add a random status

        Available placeholders:

        **{GUILDS}**  Replaced with the amount of guilds the bot is in
        **{MEMBERS}**  Replaced with the amount of members that the bot can see in every guild
        **{SHARD}**  Replaced with the bot's shard ID
        **{SHARDS}**  Replaced with the total amount of shards the bot has loaded
        **{COMMANDS}**  Replaced with the amount of commands loaded
        **{COGS}**  Replaced with the amount of cogs loaded

        You can use `[p]rndstatus parse` to test your status strings"""
        async with self.config.statuses() as statuses:
            if status.lower() in [x.lower() for x in statuses]:
                await ctx.send(error("That status already exists"))
                return
            statuses.append(status)
            await ctx.tick()

    @rndstatus.command(name="parse")
    async def rndstatus_parse(self, ctx: RedContext, *, status: str):
        """Attempt to parse a given status string

        See `[p]help rndstatus add` for the list of available placeholders

        **NOTE:** The shard placeholder will return a random shard number if this command is ran in direct messages.
        Otherwise, the shard ID for the guild this command is ran in will be used"""
        shard = randint(1, self.bot.shard_count) if ctx.guild is None else ctx.guild.shard_id + 1
        try:
            result = self.format_status(status)
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

        You can retrieve the ID for a status with [p]rndstatus list"""
        statuses = [x for x in statuses if x > 0]
        if len(statuses) == 0:
            await ctx.send_help()
            return

        bot_statuses = list(await self.config.statuses())
        for status in statuses:
            if len(bot_statuses) < status:
                await ctx.send(error("The status {} doesn't exist".format(status)))
                return
            bot_statuses[status - 1] = None

        _statuses = [x for x in bot_statuses if x is not None]  # Clear out None entries
        bot_statuses = _statuses
        await self.config.statuses.set(bot_statuses)
        if len(bot_statuses) == 0:
            await self.bot.change_presence(game=None, status=self.bot.guilds[0].me.status)
        await ctx.send(info("Removed {} status{} successfully".format(len(statuses),
                                                                      "es" if len(statuses) > 1 else "")))

    @rndstatus.command(name="list")
    async def rndstatus_list(self, ctx: RedContext, parse: bool=False):
        """Lists all set statuses

        If parse is passed, all status strings are shown as their parsed output, similarly to `[p]rndstatus parse`
        Invalid placeholders will still be identified and marked without enabling parse mode"""
        orig_statuses = list(await self.config.statuses())
        if not len(orig_statuses):
            await ctx.send(warning("I have no random statuses setup! Use `{}rndstatus add` to add some!"
                                   .format(ctx.prefix)))
            return
        statuses = []
        shard = randint(1, self.bot.shard_count) if getattr(ctx, "guild", None) is None else ctx.guild.shard_id + 1
        for item in orig_statuses:
            try:
                self.format_status(item)  # Attempt to parse the string
                if parse:
                    s = self.format_status(item).format(SHARD=shard)
                    if s != item:
                        statuses.append("{} [parsed output]".format(s))
                    else:
                        statuses.append(s)
                else:
                    statuses.append(item)
            except KeyError as e:
                statuses.append("{0} [placeholder {1!s} does not exist]".format(item, e))
        status_list = ["[{}] {}".format(statuses.index(x) + 1, x) for x in statuses]
        await ctx.send_interactive(messages=pagify("\n".join(status_list), delims=["\n"], escape_mass_mentions=True,
                                                   page_length=1990), box_lang="ini")

    @rndstatus.command(name="clear")
    async def rndstatus_clear(self, ctx: RedContext):
        """Clears all set statuses"""
        await self.config.statuses.set([])
        await self.bot.change_presence(game=None, status=self.bot.guilds[0].me.status)
        await ctx.tick()

    def format_status(self, status: str):
        members = 0
        for guild in self.bot.guilds:
            members += guild.member_count
        return status.format(
            GUILDS=len(self.bot.guilds),
            SHARDS=self.bot.shard_count,
            COGS=len(self.bot.cogs),
            COMMANDS=len(self.bot.all_commands),
            MEMBERS=members,
            SHARD="{SHARD}"  # noop to allow for this to be handled by update_status / [p]rndstatus list|parse
        )                    # without throwing a KeyError

    async def update_status(self, statuses: List[str]):
        if not statuses:
            return
        try:
            game = self.format_status(choice(statuses))
        except KeyError:
            pass
        else:
            if game is None:
                return
            for shard in [x.id for x in self.bot.shards.values()]:
                game = discord.Game(name=game.format(SHARD=shard+1))
                await self.bot.change_presence(game=game,
                                               # If this isn't provided, discord.py sets the bot's status to Online,
                                               # ignoring any previously set status - this depends on the bot being
                                               # in at least one guild
                                               status=self.bot.guilds[0].me.status,
                                               # Individually set the status of each shard
                                               # Doing this enables the possibility of the {SHARD} placeholder
                                               shard_id=shard)

    async def timer(self):
        while self == self.bot.get_cog("RNDStatus"):
            statuses = await self.config.statuses()
            await self.update_status(list(statuses))
            await asyncio.sleep(int(await self.config.delay()))
