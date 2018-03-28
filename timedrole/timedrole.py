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
from cog_shared.odinair_libs.menus import PaginateMenu


class TimedRole:
    """Give users roles for a set amount of time"""

    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = "1.1.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=35235234, force_registration=True)
        self.config.register_member(roles=[])
        GuildRoles.config = self.config
        self._expiry_task = self.bot.loop.create_task(self.remove_expired_roles())
        self._reapply_task = self.bot.loop.create_task(self.reapply_missing_roles())

    def __unload(self):
        self._expiry_task.cancel()
        self._reapply_task.cancel()

    async def add_roles(self, *roles: discord.Role, member: discord.Member, granted_by: discord.Member,
                        duration: timedelta, reason: str = None, hidden: bool = False, modlog_type: str = None):
        roles = list(roles)
        for role in roles:
            if role.is_default() or role in member.roles:
                roles.remove(role)
        if not roles:
            raise ValueError(_("No roles were given, or the only roles given were roles the member already has"))

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

        def convert(roles_: Sequence[TempRole], page_id: int):
            page_id = page_id - 1
            for role in roles_:
                rid = ((page_id * 3) + roles_.index(role)) + 1

                _strs = [_("**❯** Timed role #{} \N{EM DASH} **Hidden role**").format(rid) if role.hidden
                         else _("**❯** Timed role #{}").format(rid),
                         _("**Member** \N{EM DASH} {}").format(role.member.mention),
                         _("**Role** \N{EM DASH} {}").format(role.role.mention)]

                if role.reason is not None:
                    _strs.append(_("**Reason** \N{EM DASH} {}").format(role.reason))

                _strs.append(
                    _("**Given by** \N{EM DASH} {} \N{EM DASH} {} ago").format(
                        getattr(role.granted_by, "mention", _("An unknown member")),
                        td_format(role.added_at - datetime.utcnow())
                    ))
                _strs.append(_("**Expires** \N{EM DASH} {}").format(role.until_expires()))

                yield "\n".join(_strs)

        def page_convert(x, page, pages):
            return discord.Embed(description="\n\n".join(list(convert(x, page))), colour=ctx.me.colour)\
                .set_footer(text=f"Page {page}/{pages}")\
                .set_author(name="Timed Roles", icon_url=ctx.guild.icon_url)

        async with PaginateMenu(ctx, pages=roles, converter=page_convert, actions={}):
            pass

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
        except ValueError as e:
            await ctx.send(warning(str(e)))
        else:
            roles = ", ".join([bold(str(x)) for x in roles])
            await ctx.send(_("Successfully granted {} to **{}** for {}").format(roles, member, td_format(duration)))

    @timedrole.command(name="remove")
    async def timedrole_expire(self, ctx: RedContext, member: discord.Member, *roles: discord.Role):
        """Remove one or all active timed roles from a member"""
        groles = GuildRoles(ctx.guild)
        mroles = await groles.all_temp_roles(member)
        for r in mroles:
            if not roles or r.role in roles:
                await r.remove()
        if not roles:
            await ctx.send(_("Removed all timed roles from member **{}**").format(member))
        else:
            await ctx.send(_("Removed roles {} from member **{}**").format(", ".join(bold(str(x)) for x in roles)))

    async def remove_expired_roles(self):
        while self == self.bot.get_cog(self.__class__.__name__):
            for guild in self.bot.guilds:
                guild = GuildRoles(guild)
                expired = await guild.expired_roles(member_has_role=False)
                for role in expired:
                    await role.remove()
            await asyncio.sleep(180)

    async def reapply_missing_roles(self):
        while self == self.bot.get_cog(self.__class__.__name__):
            for guild in self.bot.guilds:
                guild = GuildRoles(guild)
                missing_roles = await guild.active_roles(member_has_role=False)
                for role in missing_roles:
                    if role.role in role.member.roles:
                        continue
                    await role.member.add_roles(role.role, reason=_("Missing timed role reapplied"))
            await asyncio.sleep(180)

    @staticmethod
    async def on_member_join(member: discord.Member):
        guild_roles = GuildRoles(member.guild)
        roles = await guild_roles.active_roles(member, member_has_role=False)
        if member.guild.me.guild_permissions.manage_roles and roles:
            # Reapply any timed roles the member had before leaving that haven't expired
            for role in roles:
                await member.add_roles(role.role, reason=_("Timed role reapplied after member rejoin"))
