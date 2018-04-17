from typing import Optional

import discord
from discord.ext import commands

from redbot.core import checks, modlog
from redbot.core.i18n import CogI18n
from redbot.core.bot import Red, RedContext, Config
from redbot.core.utils.chat_formatting import warning
from redbot.core.utils.mod import is_allowed_by_hierarchy

from cog_shared.odinair_libs import FutureTime, cogs_loaded

try:
    from timedrole.role import TempRole
except ImportError:
    raise RuntimeError("This cog requires my 'timedrole' cog to function")

_ = CogI18n("TimedMute", __file__)


class TimedMute:
    """Mute users for a set amount of time"""
    OVERWRITE_PERMISSIONS = discord.PermissionOverwrite(speak=False, send_messages=False, add_reactions=False)

    __author__ = "odinair <odinair@odinair.xyz>"

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
            await modlog.register_casetype(name="timedmute", default_setting=True, case_str="Timed Mute",
                                           image="\N{STOPWATCH}\N{SPEAKER WITH CANCELLATION STROKE}")
        except RuntimeError:
            pass

    async def setup_overwrites(self, role: discord.Role, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        if not channel.permissions_for(channel.guild.me).manage_roles:
            return
        await channel.set_permissions(target=role, overwrite=self.OVERWRITE_PERMISSIONS,
                                      reason=_("Timed mute role permissions"))

    async def setup_role(self, guild: discord.Guild) -> discord.Role:
        # `Guild.create_role` is a coroutine. PyCharm would like to disagree.
        # noinspection PyUnresolvedReferences
        role = await guild.create_role(name="Muted", permissions=discord.Permissions.none())

        for channel in guild.channels:
            await self.setup_overwrites(role, channel)

        await self.config.guild(guild).punished_role.set(role.id)
        return role

    async def get_punished_role(self, guild: discord.Guild) -> Optional[discord.Role]:
        return discord.utils.get(guild.roles, id=await self.config.guild(guild).punished_role())

    @commands.command(aliases=["tempmute"])
    @commands.guild_only()
    @cogs_loaded("TimedRole")
    @checks.mod_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def timedmute(self, ctx: RedContext, member: discord.Member,
                        duration: FutureTime.converter(min_duration=2 * 60, strict=True),
                        *, reason: str = None):
        """Mute a user for a set amount of time.

        Muted users will not be able to send messages, add new reactions to messages
        (they can still use existing reactions), or speak in voice channels.

        Examples for duration: `1h30m`, `3d`, `1mo`.
        Longer form values (such as '2 hours') are also accepted, but must be wrapped
        in double quotes if they contain spaces.

        Abbreviations: `s` for seconds, `m` for minutes, `h` for hours, `d` for days,
        `w` for weeks, `mo` for months, `y` for years.

        `m` assumes minutes instead of months.

        One month is counted as 30 days, and one year is counted as 365 days.
        Minimum duration for a mute is 2 minutes.

        Expired mutes are checked alongside expired timed roles assigned with
        `[p]timedrole`.
        """
        mod_cog = self.bot.get_cog('Mod')
        if mod_cog and not await is_allowed_by_hierarchy(bot=ctx.bot, settings=mod_cog.settings, guild=ctx.guild,
                                                         mod=ctx.author, user=member):
            await ctx.send(warning(_("This action is not allowed by your guild's hierarchy settings")))
            return

        role = await self.get_punished_role(ctx.guild)
        if role is None:
            tmp_msg = await ctx.send(_("Setting up this guild's muted role...\n"
                                       "(this may take a while, depending on how many channels you have)"))
            async with ctx.typing():
                role = await self.setup_role(ctx.guild)
            await tmp_msg.delete()

        if role in member.roles:
            await ctx.send(warning(_("That member is already muted!")))
            return

        role = await TempRole.create(member, role, duration=duration, added_by=ctx.author, reason=reason)
        await role.apply_role(reason=reason)

        try:
            await modlog.create_case(bot=self.bot, guild=ctx.guild, user=member, moderator=ctx.author,
                                     reason=reason, until=role.expires_at, action_type="timedmute",
                                     created_at=role.added_at)
        except RuntimeError:
            pass
        await ctx.tick()

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        guild = channel.guild
        if not channel.permissions_for(guild.me).manage_roles:
            return
        role = await self.get_punished_role(guild)
        if not role:
            return
        await self.setup_overwrites(role, channel)
