import discord
from discord.ext import commands

from redbot.core import checks, RedContext, Config
from redbot.core.bot import Red
from redbot.core.i18n import CogI18n
from redbot.core.utils.chat_formatting import error, box

_ = CogI18n("BotMonitor", __file__)


class BotMonitor:
    """Monitor your bots and log when one of them goes offline, and when they come back online"""

    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = "0.1.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=63213213, force_registration=True)
        self.config.register_global(monitor_bots=[], monitor_channel=None)
        self._bots = None

    @commands.group()
    @checks.is_owner()
    async def botmonitor(self, ctx: RedContext):
        if self._bots is None:
            self._bots = list(await self.config.monitor_bots())
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @botmonitor.command()
    async def watch(self, ctx: RedContext, *, bot: discord.Member):
        """Start watching a bot"""
        if not bot.bot:
            await ctx.send(error(_("The passed member is not on a bot account")))
            return
        async with self.config.monitor_bots() as bots:
            bots.append(bot.id)
            self._bots.append(bot.id)
            await ctx.tick()

    @botmonitor.command()
    async def unwatch(self, ctx: RedContext, *, bot: discord.Member):
        """Stop watching a bot"""
        if not bot.bot:
            await ctx.send(error(_("The passed member is not a bot account")))
            return
        async with self.config.monitor_bots() as bots:
            if bot.id not in bots:
                await ctx.send(error(_("I'm not currently monitoring that bot")))
                return
            bots.remove(bot.id)
            self._bots.remove(bot.id)
            await ctx.tick()

    @botmonitor.command()
    @commands.guild_only()
    async def channel(self, ctx: RedContext, channel: discord.TextChannel):
        """Set the channel the bot monitor logs to"""
        await self.config.monitor_channel.set(getattr(channel, "id", None))
        await ctx.tick()

    @botmonitor.command()
    @commands.guild_only()
    async def list(self, ctx: RedContext):
        """Returns a list of the bots this bot is monitoring"""
        bots = list(await self.config.monitor_bots())
        if not bots:
            await ctx.send(error(_("I'm not currently monitoring any bots")))
            return
        await ctx.send(box(", ".join([f"{ctx.guild.get_member(x) or _('Unknown bot')!s}" for x in bots])))

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if self._bots is None:
            self._bots = list(await self.config.monitor_bots())

        if not all([after.id in self._bots, before.status != after.status,
                    discord.Status.offline in (before.status, after.status)]):
            return
        destination = self.bot.get_channel(await self.config.monitor_channel())
        if destination is None or not isinstance(destination, discord.TextChannel) \
                or after.guild.id != destination.guild.id:
            return
        await destination.send(self.parse_status(after))

    @staticmethod
    def parse_status(bot: discord.Member):
        if bot.status == discord.Status.offline:
            return _("\N{HEAVY EXCLAMATION MARK SYMBOL} {} just went offline").format(bot.mention)
        else:
            return _("\N{WHITE HEAVY CHECK MARK} {} just came back online").format(bot.mention)
