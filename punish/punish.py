from datetime import datetime, timedelta

import discord
from discord.ext import commands

from redbot.core import checks, modlog
from redbot.core.bot import Red, RedContext, Config
from redbot.core.utils.chat_formatting import warning, info

from odinair_libs.converters import TimeDuration
from odinair_libs.checks import cogs_loaded
from odinair_libs.formatting import td_format


class Punish:
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=12903812, force_registration=True)
        self.config.register_guild(
            punished_role=None  # This is an ID of the guild's punished role
        )
        self.bot.loop.create_task(self._setup_cases())

    @staticmethod
    async def _setup_cases():
        try:
            await modlog.register_casetype(name="punish", default_setting=True,
                                           image="\N{FACE WITHOUT MOUTH}", case_str="Punish")
        except RuntimeError:
            pass

    @staticmethod
    async def add_overwrite(role: discord.Role, channel: discord.abc.GuildChannel):
        if isinstance(channel, discord.TextChannel):
            await channel.set_permissions(target=role, overwrite=discord.PermissionOverwrite(send_messages=False,
                                                                                             add_reactions=False),
                                          reason="Punished role permissions")
        elif isinstance(channel, discord.VoiceChannel):
            await channel.set_permissions(target=role, overwrite=discord.PermissionOverwrite(speak=False),
                                          reason="Punished role permissions")

    async def setup_role(self, guild: discord.Guild):
        # > create_role is async
        # > Class 'Role' does not define __await__
        # ??????????????????
        # noinspection PyUnresolvedReferences
        role = await guild.create_role(
            name="Punished",
            permissions=discord.Permissions.none(),
            reason="Setting up punish command"
        )
        # Setup channel overwrites
        for channel in guild.channels:
            await self.add_overwrite(role, channel)
        # Save role ID
        await self.config.guild(guild).punished_role.set(role.id)
        return role

    async def get_punished_role(self, guild: discord.Guild, create: bool = True):
        set_role = await self.config.guild(guild).punished_role()
        set_role = discord.utils.get(guild.roles, id=set_role)
        if set_role is None and create is True:
            set_role = await self.setup_role(guild)
        return set_role

    @commands.command()
    @commands.guild_only()
    @cogs_loaded("TimedRole")
    @checks.mod_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def punish(self, ctx: RedContext, member: discord.Member,
                     duration: TimeDuration(max_duration=timedelta(days=365).total_seconds()),
                     *, reason: str=None):
        """Punish a user for a set amount of time.

        Punished users will not be able to send messages, add new reactions to messages, or speak in voice channels.

        Examples for duration: `5d`, `1mo`, `2mo3w4d5m6s`

        Abbreviations: `s` for seconds, `m` for minutes, `h` for hours, `d` for days, `w` for weeks,
        `mo` for months, `y` for years. Any longer abbreviation is accepted. `m` assumes minutes instead of months.

        One month is counted as 30 days, and one year is counted as 365 days. All invalid abbreviations are ignored.

        Maximum duration for a punishment is one year. Expired punishments are checked every 5 minutes."""
        if duration is False:
            await ctx.send(warning("That duration is invalid"))
            return
        role = await self.get_punished_role(ctx.guild)
        try:
            await self.bot.get_cog("TimedRole").add_roles(member, ctx.author, duration,
                                                          "Punished by {}".format(ctx.author) if not reason else reason,
                                                          True, role)
        except RuntimeError as e:
            await ctx.send(warning(str(e)))
        else:
            try:
                # noinspection PyTypeChecker
                await modlog.create_case(guild=ctx.guild, created_at=datetime.utcnow(),
                                         until=(datetime.utcnow() + duration).timestamp(),
                                         action_type="punish",
                                         user=member, moderator=ctx.author, reason=reason)
            except RuntimeError:
                pass
            await ctx.tick()
            await ctx.send(info("**{}** is now punished for for {}".format(member, td_format(duration))))

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        if not channel.permissions_for(guild.me).manage_roles:
            return
        role = await self.get_punished_role(guild, create=False)
        if not role:
            return
        await self.add_overwrite(role, channel)
