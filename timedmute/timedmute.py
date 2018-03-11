import discord
from discord.ext import commands

from redbot.core import checks, modlog
from redbot.core.bot import Red, RedContext, Config
from redbot.core.utils.chat_formatting import warning
from redbot.core.utils.mod import is_allowed_by_hierarchy

from odinair_libs.converters import FutureTime
from odinair_libs.checks import cogs_loaded
from odinair_libs.formatting import td_format, tick


class TimedMute:
    CHANNEL_OVERWRITES = discord.PermissionOverwrite(speak=False, send_messages=False, add_reactions=False)

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=12903812, force_registration=True)
        self.config.register_guild(
            punished_role=None  # This is an ID of the guild's punished role
        )
        self._cases_task = self.bot.loop.create_task(self._setup_cases())

    def __unload(self):
        self._cases_task.cancel()

    @staticmethod
    async def _setup_cases():
        try:
            await modlog.register_casetype(name="timedmute", default_setting=True,
                                           image="\N{STOPWATCH}\N{SPEAKER WITH CANCELLATION STROKE}",
                                           case_str="Timed Mute")
        except RuntimeError:
            pass

    async def add_overwrite(self, role: discord.Role, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        if not channel.permissions_for(channel.guild.me).manage_roles:
            return
        await channel.set_permissions(
            target=role, overwrite=self.CHANNEL_OVERWRITES, reason="Timed mute role permissions")

    async def create_role(self, guild: discord.Guild):
        # > create_role is a coroutine
        # > Class 'Role' does not define __await__
        # ??????????????????
        # noinspection PyUnresolvedReferences
        role = await guild.create_role(name="Muted", permissions=discord.Permissions.none())
        # Setup channel overwrites
        for channel in guild.channels:
            await self.add_overwrite(role, channel)
        # Save role ID
        await self.config.guild(guild).punished_role.set(role.id)
        return role

    async def get_punished_role(self, guild: discord.Guild, create: bool = True):
        role = discord.utils.get(guild.roles, id=await self.config.guild(guild).punished_role())
        if role is None and create is True:
            role = await self.create_role(guild)
        return role

    max_duration = FutureTime.get_seconds('2 years')
    min_duration = FutureTime.get_seconds('2 minutes')

    @commands.command(aliases=["tempmute"])
    @commands.guild_only()
    @cogs_loaded("TimedRole")
    @checks.mod_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def timedmute(self, ctx: RedContext, member: discord.Member,
                        duration: FutureTime.converter(max_duration=max_duration, min_duration=min_duration,
                                                       strict=True),
                        *, reason: str=None):
        """Mute a user for a set amount of time.

        Muted users will not be able to send messages, add new reactions to messages, or speak in voice channels.

        Examples for duration: `1h30m`, `3d`, `1mo`

        Abbreviations: `s` for seconds, `m` for minutes, `h` for hours, `d` for days, `w` for weeks,
        `mo` for months, `y` for years. Any longer abbreviation is accepted. `m` assumes minutes instead of months.

        One month is counted as 30 days, and one year is counted as 365 days.
        Maximum duration for a mute is 2 years.

        Expired mutes are checked alongside expired timed roles assigned with `[p]timedrole`
        """
        mod_cog = self.bot.get_cog('Mod')
        if mod_cog and not await is_allowed_by_hierarchy(bot=ctx.bot, settings=mod_cog.settings, guild=ctx.guild,
                                                         mod=ctx.author, user=member):
            await ctx.send(warning("This action is not allowed by your guild's hierarchy settings"))
            return
        role = await self.get_punished_role(ctx.guild, create=False)
        if role is None:
            tmp_msg = await ctx.send("Setting up muted role...\n"
                                     "(this may take a while, depending on how many channels you have)")
            async with ctx.typing():
                role = await self.create_role(ctx.guild)
            await tmp_msg.delete()
        try:
            audit_reason = f"Muted by {ctx.author!s} (ID {ctx.author.id})."
            if reason is not None:
                audit_reason = f"{audit_reason} Reason: {reason}"
            timed_role = self.bot.get_cog("TimedRole")
            await timed_role.add_roles(role, member=member, duration=duration, granted_by=ctx.author,
                                       reason=audit_reason, expired_reason="Timed mute expired",
                                       hidden=True, modlog_type="timedmute", modlog_reason=reason)
        except RuntimeError as e:
            await ctx.send(warning(str(e)))
        else:
            await ctx.send(tick(f"**{member!s}** is now muted for for {td_format(duration)}"))

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        guild = channel.guild
        if not channel.permissions_for(guild.me).manage_roles:
            return
        role = await self.get_punished_role(guild, create=False)
        if not role:
            return
        await self.add_overwrite(role, channel)
