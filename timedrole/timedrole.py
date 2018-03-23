import asyncio
from typing import Sequence
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config, modlog
from redbot.core.utils.chat_formatting import warning, bold, escape

from timedrole.role import TempRole
from timedrole.guild import GuildRoles
from timedrole.i18n import _

from cog_shared.odinair_libs.formatting import td_format, chunks
from cog_shared.odinair_libs.converters import FutureTime
from cog_shared.odinair_libs.menus import paginate


class TimedRole:
    """Give users roles for a set amount of time"""

    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = "1.0.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=35235234, force_registration=True)
        self.config.register_member(roles=[])
        GuildRoles.config = self.config
        GuildRoles.bot = self.bot
        self._expiry_task = self.bot.loop.create_task(self.remove_expired_roles())

    def __unload(self):
        self._expiry_task.cancel()

    async def add_roles(self, *roles: discord.Role, member: discord.Member, granted_by: discord.Member,
                        duration: timedelta, reason: str = None, hidden: bool = False, modlog_type: str = None):
        """Adds roles to a member.

        Parameters
        -----------
        *roles: discord.Role
            A list of roles to give to a member
        member: discord.Member
            The member to add the roles to
        granted_by: discord.Member
            The member who granted the user the role(s)
        duration: timedelta
            How long to give the user the role for
        reason: str
            An optional reason that displays in [p]timedrole list.
            If `modlog_type` is not None, then this also displays as the reason for the created modlog case.
        hidden: bool
            If this is True, this role will not be displayed in [p]timedrole list
        modlog_type: str
            A modlog action type. If this is a string, a mod log case is attempted to be created.
        """
        roles = list(roles)
        if member.guild.default_role in roles:
            roles.remove(member.guild.default_role)
        if len(roles) == 0:
            raise ValueError(_("No roles were given, or the only role given was the guild's default role"))
        for role in roles:
            if role in member.roles:
                raise RuntimeError(_("That member already has the role {}").format(role))

        if duration is None:
            duration = timedelta(days=30)
        now = datetime.utcnow()
        duration = duration.total_seconds()

        await member.add_roles(*roles)

        async with self.config.member(member).roles() as member_roles:
            for role in roles:
                member_roles.append({"role_id": role.id,
                                     "added_at": now,
                                     "duration": duration,
                                     "granted_by": granted_by.id,
                                     "reason": reason,
                                     "hidden": hidden})

        if modlog_type is not None:
            try:
                # noinspection PyTypeChecker
                await modlog.create_case(guild=member.guild, action_type=modlog_type,
                                         until=(now + timedelta(seconds=duration)).timestamp(),
                                         created_at=now, user=member, moderator=granted_by,
                                         reason=reason)
            except RuntimeError:
                pass

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def timedrole(self, ctx: RedContext):
        """Timed role management"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @staticmethod
    async def _paginate(ctx: RedContext, *members: discord.Member, show_hidden: bool = False):
        guild_roles = GuildRoles(ctx.guild)
        roles = await guild_roles.all_temp_roles(*members)
        roles = list(filter(lambda x: x.hidden is not True or show_hidden is True, roles))
        roles = list(chunks(roles, 4))
        if not roles:
            await ctx.send(warning(_("This guild has no currently active timed roles") if not members else
                                   _("None of those members have any active timed roles")))
            return

        def convert(roles_: Sequence[TempRole]):
            for role in roles_:
                header = "**❯** {} \N{EM DASH} {}".format(role.member.mention, role.role.mention)
                if role.hidden:
                    header = _("**❯** {} \N{EM DASH} {} \N{EM DASH} **Hidden role**").format(
                        role.member.mention, role.role.mention)
                if role.reason is not None:
                    reason = _("**Reason** \N{EM DASH} {}").format(role.reason)
                else:
                    reason = ""
                added_delta = td_format(role.added_at - datetime.utcnow())
                given_by = _("**Given by** \N{EM DASH} {} \N{EM DASH} {} ago").format(
                    getattr(role.granted_by, "mention", _("An unknown member")), added_delta)
                expires = _("**Expires** \N{EM DASH} {}").format(role.until_expires())

                _strs = [header]
                if reason:
                    _strs.append(reason)
                _strs.append(given_by)
                _strs.append(expires)
                yield "\n".join(_strs)

        await paginate(ctx, pages=roles, page_converter=lambda r: "\n\n".join(list(convert(r))))

    @timedrole.group(name="list", invoke_without_command=True)
    async def timedrole_list(self, ctx: RedContext):
        """List all known timed roles

        Hidden timed roles can be viewed with `[p]timedrole list hidden`
        """
        await self._paginate(ctx)

    @timedrole_list.command(name="members")
    async def timedrole_list_member(self, ctx: RedContext, *members: discord.Member):
        """Lists timed roles for specific members

        Hidden timed roles applied by external cogs can be viewed with
        `[p]timedrole list hidden [members...]`
        """
        if not members:
            await ctx.send_help()
            return
        await self._paginate(ctx, *members)

    @timedrole_list.command(name="hidden")
    async def timedrole_list_hidden(self, ctx: RedContext, *members: discord.Member):
        """Lists all known timed roles, including hidden roles applied by external cogs"""
        await self._paginate(ctx, *members, show_hidden=True)

    @timedrole.command(name="add")
    async def timedrole_add(self, ctx: RedContext, member: discord.Member, duration: FutureTime.converter(strict=True),
                            *roles: discord.Role):
        """Add one or more roles to a user for a set amount of time.

        You can give a user up to 10 roles at once.

        Examples for duration: `5d`, `1mo`, `1y2mo3w4d5m6s`

        Abbreviations: `s` for seconds, `m` for minutes, `h` for hours, `d` for days, `w` for weeks,
        `mo` for months, `y` for years. Any longer abbreviation is accepted. `m` assumes minutes instead of months.

        One month is counted as 30 days, and one year is counted as 365 days. All invalid abbreviations are ignored.

        Maximum duration for a timed role is two years. Expired timed roles are checked every 3 minutes.
        """
        roles = list(roles)
        if ctx.guild.default_role in roles:
            roles.remove(ctx.guild.default_role)
        if not roles or len(roles) > 10:
            await ctx.send_help()
            return

        cannot_add = {}
        for role in roles:
            if role >= ctx.author.top_role and not ctx.guild.owner == ctx.author:
                cannot_add[role] = _("Role is equal to or above your highest ranked role")
            elif role >= ctx.me.top_role:
                cannot_add[role] = _("Role is equal to or above my highest ranked role")

        if any(cannot_add):
            cannot_add = "\n".join(f"`{escape(x.name, mass_mentions=True, formatting=True)}` "
                                   f"\N{EM DASH} {cannot_add[x]}" for x in cannot_add)
            await ctx.send(warning(f"Cannot add one or more of the given roles for the following reasons:\n\n"
                                   f"{cannot_add}"))
            return

        try:
            await self.add_roles(*roles, member=member, duration=duration, granted_by=ctx.author)
        except discord.Forbidden:
            await ctx.send(warning(_("I'm not allowed to give one or more of those roles to that user")))
        except RuntimeError as e:
            await ctx.send(warning(str(e)))
        else:
            roles = ", ".join([bold(str(x)) for x in roles])
            await ctx.send(_("Successfully granted {} to **{}** for {}").format(roles, member, td_format(duration)))

    @timedrole.command(name="expire", hidden=True)
    async def timedrole_expire(self, ctx: RedContext, member: discord.Member, role: discord.Role = None):
        """Force a role expiry, as if the time on the role had ran out

        __This command is intended to be used for debug purposes, and as such should not be used regularly.__

        You can remove a timed role from a member like any other role, and the role will be
        treated as if it expired when the bot does the next wave of expiry checks of the
        guild's timed roles.
        """
        groles = GuildRoles(ctx.guild)
        roles = await groles.all_temp_roles(member)
        for role_ in roles:
            if role_.role == role or role is None:
                await role_.remove()
        if not role:
            await ctx.send(_("Forcefully expired all roles from {}").format(member))
        else:
            await ctx.send(_("Forcefully expired role `{}` from {}").format(role.name, member))

    async def remove_expired_roles(self):
        while self == self.bot.get_cog(self.__class__.__name__):
            for guild in self.bot.guilds:
                guild = GuildRoles(guild)
                expired = await guild.expired_roles(member_has_role=False)
                for role in expired:
                    await role.remove()
            await asyncio.sleep(180)

    @staticmethod
    async def on_member_join(member: discord.Member):
        guild_roles = GuildRoles(member.guild)
        roles = await guild_roles.active_roles(member, member_has_role=False)
        if member.guild.me.guild_permissions.manage_roles and roles:
            # Reapply any timed roles the member had before leaving that haven't expired
            for role in roles:
                await member.add_roles(role.role, reason=_("Timed role reapplied after member rejoin"))
