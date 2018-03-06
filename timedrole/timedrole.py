import asyncio
from typing import Sequence, Union

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config, modlog
from redbot.core.utils.chat_formatting import warning, bold, escape

from datetime import datetime, timedelta

from odinair_libs.formatting import td_format, chunks
from odinair_libs.converters import FutureTime
from odinair_libs.menus import paginate


class GuildRoles:
    def __init__(self, config: Config, guild: discord.Guild):
        self._config = config
        self.guild = guild

    @property
    def roles(self) -> Sequence[discord.Role]:
        return self.guild.roles

    async def all_temp_roles(self, *members: discord.Member) -> Sequence["TRole"]:
        members = [x.id for x in members]
        member_data = await self._config.all_members(self.guild)
        member_data = {uid: member_data[uid] for uid in member_data
                       if not len(members) or uid in members}
        roles = []
        for uid in member_data:
            member = self.guild.get_member(uid)
            if not member:
                continue
            temp_roles = member_data[uid]["roles"]
            for temp_role in temp_roles:
                try:
                    role = TRole.from_data(self, member, temp_role)
                except ValueError:
                    await self.remove(member, temp_role.get("role_id"))
                else:
                    roles.append(role)
        return roles

    async def expired_roles(self, *members: discord.Member, **kwargs) -> Sequence["TRole"]:
        return [x for x in await self.all_temp_roles(*members) if x.check_expired(**kwargs)]

    async def active_roles(self, *members: discord.Member, **kwargs) -> Sequence["TRole"]:
        return [x for x in await self.all_temp_roles(*members) if not x.check_expired(**kwargs)]

    async def remove(self, member: discord.Member, role: discord.Role or int) -> None:
        role_id = role if isinstance(role, int) else role.id
        async with self._config.member(member).roles() as temp_roles:
            for item in temp_roles:
                if item.get("role_id", None) == role_id:
                    temp_roles.remove(item)


class TRole:
    # noinspection PyUnusedLocal
    def __init__(self, role: discord.Role, guild: GuildRoles, member: discord.Member, added_at: datetime, duration: int,
                 granted_by: int, hidden: bool = False, expired_reason: str = None, reason: str = None, **kwargs):
        self.member = member
        self.role = role
        self.guild = guild
        self.duration = timedelta(seconds=duration)
        self.added_at = added_at
        self.expiry_time = added_at + self.duration
        self.granted_by = guild.guild.get_member(granted_by) or granted_by
        self.hidden = hidden
        self._expired_reason = expired_reason
        self._reason = reason

    def __str__(self):
        return str(self.role)

    @classmethod
    def from_data(cls, guild: GuildRoles, member: discord.Member, data: dict):
        role = discord.utils.get(guild.roles, id=data.get("role_id", None))
        if role is None:
            return None
        return cls(role=role, member=member, guild=guild, **data)

    def until_expires(self, as_string: bool = False) -> Union[timedelta, str]:
        expiry_ts = self.expiry_time - datetime.utcnow()
        if as_string is False:
            return expiry_ts
        else:
            return td_format(expiry_ts, append_str=True) if expiry_ts > timedelta()\
                else "Queued for removal"

    def check_expired(self, *, member_has_role: bool = True) -> bool:
        return (self.role not in self.member.roles if member_has_role else False) \
               or self.expiry_time < datetime.utcnow()

    @property
    def has_expired(self) -> bool:
        return self.check_expired(member_has_role=True)

    @property
    def expired_reason(self) -> str:
        return self._expired_reason if self._expired_reason is not None else "Timed role expired"

    @property
    def reason(self) -> str:
        return self._reason if self._reason is not None else "Timed role granted by {0!s}".format(self.granted_by)

    async def remove(self) -> None:
        await self.guild.remove(self.member, self.role)
        if self.role in self.member.roles:
            try:
                await self.member.remove_roles(self.role, reason=self.expired_reason)
            except discord.HTTPException:
                pass


class TimedRole:
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=35235234, force_registration=True)
        self.config.register_member(roles=[])
        self._expiry_task = self.bot.loop.create_task(self.remove_expired_roles())

    def __unload(self):
        self._expiry_task.cancel()

    def get_guild(self, guild: discord.Guild):
        """Get the GuildRoles object for a Guild

        Parameters
        -----------
        guild: discord.Guild
            The guild to get the GuildRoles object for

        Returns
        --------
        GuildRoles
            The GuildRoles object for the given Guild
        """
        return GuildRoles(self.config, guild)

    async def add_roles(self, *roles: discord.Role, member: discord.Member, granted_by: discord.Member,
                        duration: timedelta, expired_reason: str = None, reason: str = None,
                        hidden: bool = False, modlog_type: str = None, modlog_reason: str = None):
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
            Optional reason that displays in the audit log.
            If this is None, a generic reason is displayed instead
        expired_reason: str
            Optional reason that displays in the audit log when the role expires.
            If this is None, a generic reason is displayed instead
        hidden: bool
            If this is True, this role will not be displayed in [p]timedrole list
        modlog_type: dict
            A modlog action type. If this is a string, a mod log case is attempted to be created.
        modlog_reason: str
            An optional reason to show in the mod log. If this is None, ``reason`` is used instead
        """
        roles = list(roles)
        if member.guild.default_role in roles:
            roles.remove(member.guild.default_role)
        if len(roles) == 0:
            raise ValueError("No roles were given, or the only role given was the guild's default role")
        for role in roles:
            if role in member.roles:
                raise RuntimeError("That member already has the role {}".format(role))

        if duration is None:
            duration = timedelta(days=30)

        now = datetime.utcnow()
        duration = duration.total_seconds()

        raw_reason = reason
        if reason is None:
            reason = "Timed role granted by {0!s}".format(granted_by)
        await member.add_roles(*roles, reason=reason)

        async with self.config.member(member).roles() as tmp_roles:
            for role in roles:
                tmp_roles.append({"role_id": role.id,
                                  "added_at": now,
                                  "duration": duration,
                                  "granted_by": granted_by.id,
                                  "reason": reason,
                                  "expired_reason": expired_reason or "Timed role expired",
                                  "hidden": hidden})

        if modlog_type is not None:
            try:
                # noinspection PyTypeChecker
                await modlog.create_case(guild=member.guild, action_type=modlog_type,
                                         until=(now + timedelta(seconds=duration)).timestamp(),
                                         created_at=now, user=member, moderator=granted_by,
                                         reason=modlog_reason or raw_reason)
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

    async def _paginate(self, ctx: RedContext, *members: discord.Member, show_hidden: bool = False):
        guild_roles = self.get_guild(ctx.guild)
        roles = await guild_roles.all_temp_roles(*members)
        roles = list(filter(lambda x: x.hidden is not True or show_hidden is True, roles))
        roles = list(chunks(roles, 4))
        if not roles:
            await ctx.send(warning("No timed roles are active on this guild" if not members else
                                   "None of those members have any active timed roles"))
            return

        def convert(roles_: Sequence[TRole]) -> str:
            strs = []
            for role in roles_:
                hidden = " \N{EM DASH} **Hidden timed role**" if role.hidden else ""
                reason = "" if role.reason.startswith("Timed role granted by") else f"\n**Reason:** `{role.reason}`"
                added_delta = role.added_at - datetime.utcnow()
                added_delta = td_format(added_delta, append_str=True)
                strs.append(f"**❯** {role.member.mention} \N{EM DASH} {role.role.mention}{hidden}\n"
                            f"{reason}\n"
                            f"**Given by** {role.granted_by.mention}\n"
                            f"**Added** {added_delta}\n"
                            f"**Expires** {role.until_expires(True)}")
            return "\n\n".join(strs)

        await paginate(ctx, pages=roles, page_converter=convert)

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
    async def timedrole_add(self, ctx: RedContext, member: discord.Member, duration: FutureTime(strict=True),
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
                cannot_add[role] = "Role is equal to or above your highest ranked role"
            elif role >= ctx.me.top_role:
                cannot_add[role] = "Role is equal to or above my highest ranked role"

        if any(cannot_add):
            cannot_add = "\n".join(f"`{escape(x.name, mass_mentions=True, formatting=True)}` "
                                   f"\N{EM DASH} {cannot_add[x]}" for x in cannot_add)
            await ctx.send(warning(f"Cannot add one or more of the given roles for the following reasons:\n\n"
                                   f"{cannot_add}"))
            return

        try:
            await self.add_roles(*roles, member=member, duration=duration, granted_by=ctx.author)
        except discord.Forbidden:
            await ctx.send(warning("I'm not allowed to give one or more of those roles to that user"))
        except RuntimeError as e:
            await ctx.send(warning(str(e)))
        else:
            roles_ = ", ".join([bold(str(x)) for x in roles])
            await ctx.send(f"Successfully granted {roles_} to **{member!s}** for {td_format(duration)}")

    @timedrole.command(name="expire", hidden=True)
    async def timedrole_expire(self, ctx: RedContext, member: discord.Member, role: discord.Role = None):
        """Force a role expiry, as if the time on the role had ran out

        __This command is intended to be used for debug purposes, and as such should not be used regularly.__

        You can remove a timed role from a member like any other role, and the role will be
        treated as if it expired when the bot does the next wave of expiry checks of the
        guild's timed roles.
        """
        groles = GuildRoles(self.config, ctx.guild)
        roles = await groles.all_temp_roles(member)
        for role_ in roles:
            if role_.role == role or role is None:
                await role_.remove()
        role_name = role.name if role else "all"
        plural = "s" if not role else ""
        await ctx.send(f"Forcefully expired {role_name} role{plural}")

    async def remove_expired_roles(self):
        while self == self.bot.get_cog(self.__class__.__name__):
            for guild in self.bot.guilds:
                guild = self.get_guild(guild)
                expired = await guild.expired_roles()
                for role in expired:
                    await role.remove()
            await asyncio.sleep(180)

    async def on_member_join(self, member: discord.Member):
        guild_roles = self.get_guild(member.guild)
        roles = await guild_roles.active_roles(member, member_has_role=False)
        if member.guild.me.guild_permissions.manage_roles and roles:
            # Reapply any timed roles the member had before leaving that haven't expired
            for role in roles:
                await member.add_roles(role.role, reason="Timed role reapplied after member rejoin")
