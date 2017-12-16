import asyncio
from typing import List

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import Config, checks
from redbot.core.utils.chat_formatting import error, pagify

from random import choice


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
    async def rndstatus_delay(self, ctx: RedContext, delay: int):
        """Set the amount of time required to pass in seconds to change the bot's playing status

        Minimum amount of seconds between changes is 60
        Default delay is every 5 minutes, or every 300 seconds"""
        if delay < 60:
            await ctx.send_help()
            return
        await self.config.delay.set(delay)
        await ctx.tick()

    @rndstatus.command(name="add")
    async def rndstatus_add(self, ctx: RedContext, *, status: str):
        """Add a random status

        Available replacement strings:

        **{MEMBERS}**
            Replaced with the amount of members that the bot can see in every guild
        **{GUILDS}**
            Replaced with the amount of guilds the bot is in
        **{SHARDS}**
            Replaced with the total amount of shards the bot has loaded
        **{COMMANDS}**
            Replaced with the amount of commands loaded
        **{COGS}**
            Replaced with the amount of cogs loaded"""
        async with self.config.statuses() as statuses:
            if status.lower() in [x.lower() for x in statuses]:
                await ctx.send(error("That status already exists"))
                return
            statuses.append(status)
            await ctx.tick()

    @rndstatus.command(name="remove", aliases=["delete"])
    async def rndstatus_remove(self, ctx: RedContext, status: int):
        """Remove a status by ID

        You can retrieve the ID for a status with [p]rndstatus list"""
        async with self.config.statuses() as statuses:
            if len(statuses) < status:
                await ctx.send(error("That status doesn't exist"))
                return
            del statuses[status - 1]
            await ctx.tick()

    @rndstatus.command(name="list")
    async def rndstatus_list(self, ctx: RedContext):
        """Lists all set statuses"""
        statuses = list(await self.config.statuses())
        status_list = ["{}: {}".format(statuses.index(x) + 1, x) for x in statuses]
        await ctx.send_interactive(messages=pagify("\n".join(status_list), delims=["\n"], escape_mass_mentions=True),
                                   box_lang="python")

    @rndstatus.command(name="clear")
    async def rndstatus_clear(self, ctx: RedContext):
        """Clears all set statuses"""
        await self.config.statuses.set([])
        await self.bot.change_presence(game=None)
        await ctx.tick()

    async def _update_status(self, statuses: List[str]):
        if statuses:
            game = choice(statuses)
            members = 0
            for guild in self.bot.guilds:
                for _ in guild.members:
                    members += 1
            try:
                game = game.format(
                    GUILDS=len(self.bot.guilds),
                    SHARDS=self.bot.shard_count,
                    COGS=len(self.bot.cogs),
                    COMMANDS=len(self.bot.all_commands),
                    MEMBERS=members
                )
            except KeyError:
                return
            game = discord.Game(name=game)
            await self.bot.change_presence(game=game,
                                           # If this isn't provided, discord.py sets the bot's status to Online,
                                           # ignoring any previously set status - this depends on the bot being
                                           # in at least one guild
                                           status=self.bot.guilds[0].me.status)

    async def timer(self):
        while self == self.bot.get_cog("RNDStatus"):
            statuses = await self.config.statuses()
            await self._update_status(list(statuses))
            await asyncio.sleep(int(await self.config.delay()))
