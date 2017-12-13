import asyncio

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import Config, checks
from redbot.core.utils.chat_formatting import error

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
    async def _rndstatus(self, ctx: RedContext):
        """Manage random statuses"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @_rndstatus.command(name="delay")
    async def _rndstatus_delay(self, ctx: RedContext, delay: int):
        """Set the amount of time required to pass in seconds

        Minimum amount of seconds between changes is 60
        Default delay is every 5 minutes, or every 300 seconds"""
        if delay < 60:
            await ctx.send_help()
            return
        await self.config.delay.set(delay)
        await ctx.tick()

    @_rndstatus.command(name="add")
    async def _rndstatus_add(self, ctx: RedContext, *, status: str):
        """Add a random status

        Available replacement strings:

        {TOTAL_MEMBERS} - replaced with the amount of members that the bot can see globally
        {GUILDS} - replaced with the amount of guilds the bot is in
        {SHARDS} - replaced with the total amount of shards the bot has
        {COMMANDS} - replaced with the amount of commands loaded
        {COGS} - replaced with the amount of cogs loaded"""
        async with self.config.statuses() as statuses:
            if status.lower() in [x.lower() for x in statuses]:
                await ctx.send(error("That status already exists"))
                return
            statuses.append(status)
            await ctx.tick()

    @_rndstatus.command(name="remove", aliases=["delete"])
    async def _rndstatus_remove(self, ctx: RedContext, status: int):
        """Remove a status by ID

        You can retrieve the ID for a status with [p]rndstatus list"""
        async with self.config.statuses() as statuses:
            if len(statuses) < status:
                await ctx.send(error("That status doesn't exist"))
                return
            del statuses[status - 1]
            await ctx.tick()

    @_rndstatus.command(name="list")
    async def _rndstatus_list(self, ctx: RedContext):
        """Lists all set statuses"""
        # I don't exactly see anyone getting enough statuses to reach the length required for a second page
        # But hey, I wanted to use send_interactive at least once
        statuses = list(await self.config.statuses())
        status_str = []
        current = []
        for item in statuses:
            if len("\n".join(current)) > 1500:
                status_str.append("\n".join(current))
                current = ""
            current.append("{}: \"{}\"".format(statuses.index(item) + 1, item.replace("\"", "\\\"")))
        if len(current) > 0:
            status_str.append(",\n".join(current))
        await ctx.send_interactive(messages=status_str, box_lang="python")

    @_rndstatus.command(name="clear")
    async def _rndstatus_clear(self, ctx: RedContext):
        """Clears all set statuses"""
        await self.config.statuses.set([])
        await self.bot.change_presence(game=None)
        await ctx.tick()

    async def timer(self):
        while self == self.bot.get_cog("RNDStatus"):
            statuses = await self.config.statuses()
            if statuses:
                game = choice(list(await self.config.statuses()))
                members = 0
                for guild in self.bot.guilds:
                    # noinspection PyUnusedLocal
                    for member in guild.members:
                        members += 1
                game = game.format(
                    GUILDS=len(self.bot.guilds),
                    SHARDS=self.bot.shard_count,
                    COGS=len(self.bot.cogs),
                    COMMANDS=len(self.bot.all_commands),
                    TOTAL_MEMBERS=members
                )
                game = discord.Game(name=game)
                await self.bot.change_presence(game=game,
                                               # Hacky workaround for the user status
                                               # If this isn't provided, discord.py clears the set status
                                               # This depends on the bot being in at least one guild
                                               status=self.bot.guilds[0].me.status)
            await asyncio.sleep(int(await self.config.delay()))
