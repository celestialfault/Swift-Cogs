import discord
from discord.ext import commands

from redbot.core import checks, RedContext, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import error, box


class FakeMember:

    # noinspection PyShadowingBuiltins
    def __init__(self, id, status, guild, name, discriminator):
        self.id = id
        self.name = name
        self.discriminator = discriminator
        self.status = status
        self.guild = guild

    def __str__(self):
        # tfw can't add __str__ to a namedtuple
        return "{0.name}#{0.discriminator}".format(self)


class BotMonitor:
    """Monitor your bots and log when one of them goes offline, and when they come back online"""
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=63213213, force_registration=True)
        self.config.register_global(monitor_bots=[], monitor_channel=None)

    @commands.group()
    @checks.is_owner()
    async def botmonitor(self, ctx: RedContext):
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @botmonitor.command(name="monitor", aliases=["watch"])
    async def botmonitor_monitor(self, ctx: RedContext, *, bot: discord.Member):
        """Start watching a bot"""
        if not bot.bot:
            await ctx.send(error("The passed member is not on a bot account"))
            return
        async with self.config.monitor_bots() as bots:
            bots.append(bot.id)
            await ctx.tick()

    @botmonitor.command(name="unmonitor", aliases=["unwatch"])
    async def botmonitor_unmonitor(self, ctx: RedContext, *, bot: discord.Member):
        """Stop watching a bot"""
        if not bot.bot:
            await ctx.send(error("The passed member is not on a bot account"))
            return
        async with self.config.monitor_bots() as bots:
            if bot.id not in bots:
                await ctx.send(error("I'm not currently monitoring that bot"))
                return
            bots.remove(bot.id)
            await ctx.tick()

    @botmonitor.command(name="channel")
    async def botmonitor_channel(self, ctx: RedContext, channel: discord.TextChannel):
        """Set the channel the bot monitor logs to"""
        await self.config.monitor_channel.set(getattr(channel, "id", None))
        await ctx.tick()

    @botmonitor.command(name="list", aliases=["bots"])
    async def botmonitor_list(self, ctx: RedContext):
        bots = list(await self.config.monitor_bots())
        if not bots:
            await ctx.send(error("I'm not currently monitoring any bots"))
            return
        await ctx.send(box(", ".join([str(ctx.guild.get_member(x)) for x in bots])))

    @botmonitor.command(name="fake")
    async def botmonitor_fake(self, ctx: RedContext, bot: discord.Member, online: bool = False):
        """Fake a bot update.

        If online is True, this fakes a bot coming back online, otherwise it fakes a bot going offline"""
        if not bot.bot:
            await ctx.send(error("The passed member is not on a bot account"))
            return

        before = FakeMember(id=bot.id, status=discord.Status.online if not online else discord.Status.offline,
                            guild=ctx.guild, name=bot.name, discriminator=bot.discriminator)
        after = FakeMember(id=bot.id, status=discord.Status.offline if not online else discord.Status.online,
                           guild=ctx.guild, name=bot.name, discriminator=bot.discriminator)

        await self.on_member_update(before, after)

    async def on_member_update(self, before: discord.Member or FakeMember, after: discord.Member or FakeMember):
        if after.id not in list(await self.config.monitor_bots()):
            return
        destination = self.bot.get_channel(await self.config.monitor_channel())
        if destination is None or not isinstance(destination, discord.TextChannel):
            return
        if after.guild.id != destination.guild.id:
            # I'm not sure if discord.py sends multiple member update events for each guild the bots share
            # if only the bot's status changes, but probably a good idea to check regardless
            return
        if before.status == after.status or discord.Status.offline not in (before.status, after.status):
            return
        await destination.send(self.parse_status(after))

    @staticmethod
    def parse_status(bot: discord.Member):
        status = bot.status
        return "{emoji} **{bot!s}** just {status_str}".format(bot=bot,
                                                              emoji="\N{HEAVY EXCLAMATION MARK SYMBOL}"
                                                              if status == discord.Status.offline
                                                              else "\N{WHITE HEAVY CHECK MARK}",
                                                              status_str="went offline"
                                                              if status == discord.Status.offline
                                                              else "came back online")
