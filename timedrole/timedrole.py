import asyncio
from typing import List

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import warning, bold, pagify

from datetime import datetime, timedelta

from odinair_libs.formatting import td_format
from odinair_libs.converters import FutureTime


class GuildRoles:
    def __init__(self, config: Config, guild: discord.Guild):
        self._config = config
        self.guild = guild

    @property
    def roles(self):
        return self.guild.roles

    async def all_temp_roles(self, *members: discord.Member):
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

    async def expired_roles(self, *members: discord.Member, **kwargs):
        return [x for x in await self.all_temp_roles(*members) if x.check_expired(**kwargs)]

    async def active_roles(self, *members: discord.Member, **kwargs):
        return [x for x in await self.all_temp_roles(*members) if not x.check_expired(**kwargs)]

    async def remove(self, member: discord.Member, role: discord.Role or int):
        role_id = role if isinstance(role, int) else role.id
        async with self._config.member(member).roles() as temp_roles:
            for item in temp_roles:
                if item.get("role_id", None) == role_id:
                    temp_roles.remove(item)


class TRole:
    def __init__(self, role: discord.Role, guild: GuildRoles, member: discord.Member, given_at: datetime, seconds: int,
                 granted_by: discord.Member, hidden: bool = False, expired_reason: str = None, reason: str = None):
        self.member = member
        self.role = role
        self.guild = guild
        self.expiry_time = given_at + timedelta(seconds=seconds)
        self.granted_by = granted_by
        self.hidden = hidden
        self._expired_reason = expired_reason
        self._reason = reason

    @classmethod
    def from_data(cls, guild: GuildRoles, member: discord.Member, data: dict):
        role = discord.utils.get(guild.roles, id=data.get("role_id", None))
        if role is None:
            raise ValueError("Data does not contain a role ID, or the role was deleted")
        return cls(role=role, member=member, guild=guild, given_at=data.get("added_at"), seconds=data.get("duration"),
                   granted_by=guild.guild.get_member(data.get("granted_by")), hidden=data.get("hidden", False),
                   expired_reason=data.get("expired_reason", None), reason=data.get("reason", None))

    def until_expires(self, as_string: bool = False):
        expiry_ts = self.expiry_time - datetime.utcnow()
        if as_string is False:
            return expiry_ts
        else:
            return td_format(expiry_ts) if expiry_ts > timedelta() else "Queued for removal"

    def check_expired(self, *, member_has_role: bool = True):
        return (self.role not in self.member.roles if member_has_role else False) \
               or self.expiry_time < datetime.utcnow()

    @property
    def has_expired(self):
        return self.check_expired(member_has_role=True)

    @property
    def expired_reason(self):
        return self._expired_reason if self._expired_reason is not None else "Timed role expired"

    @property
    def reason(self):
        return self._reason if self._reason is not None else "Timed role granted by {0!s}".format(self.granted_by)

    async def remove(self):
        await self.guild.remove(self.member, self.role)
        if self.role in self.member.roles:
            try:
                await self.member.remove_roles(self.role, reason=self.expired_reason)
            except discord.Forbidden:
                pass


class TimedRole:
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=35235234, force_registration=True)
        self.config.register_member(roles=[])
        self.bot.loop.create_task(self.remove_expired_roles())

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

    async def add_roles(self, member: discord.Member, granted_by: discord.Member, duration: timedelta,
                        roles: List[discord.Role], expired_reason: str = None, reason: str = None,
                        hidden: bool = False):
        """Adds roles to a member.

        Parameters
        -----------

            member: discord.Member

                The member to add the roles to

            granted_by: discord.Member

                The member who granted the user the role(s)

            duration: timedelta

                How long to give the user the role for

            roles: List[discord.Role]

                A list of roles to give the member

            reason: str

                Optional reason that displays in the audit log.
                If this is None, a generic reason is displayed instead

            expired_reason: str

                Optional reason that displays in the audit log when the role expires.
                If this is None, a generic reason is displayed instead

            hidden: bool

                If this is True, this role will not be displayed in [p]timedrole list
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

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def timedrole(self, ctx: RedContext):
        """Timed role management"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @timedrole.command(name="list")
    async def list_roles(self, ctx: RedContext, *members: discord.Member):
        """List all members with timed roles"""
        guild_roles = self.get_guild(ctx.guild)
        roles = await guild_roles.all_temp_roles(*members)
        strings = []
        members_ = {}
        for role in roles:
            if role.hidden is True:
                continue
            if role.member not in members_:
                members_[role.member] = []
            members_[role.member].append("**❯** Role: **{role!s}**\n"
                                         "      Granted by: **{granted_by!s}**\n"
                                         "      Expires in: **{duration}**".format(role=role.role,
                                                                                   granted_by=role.granted_by,
                                                                                   duration=role.until_expires(True)))
        for member in members_:
            roles = members_[member]
            strings.append("Member **{0!s}**:\n{1}".format(member, "\n".join(roles)))
        if not strings:
            await ctx.send(warning("There's no members in this server with any timed roles"
                                   if not members else "None of those members have active timed roles"))
        await ctx.send_interactive(pagify("\n\n".join(strings), escape_mass_mentions=True))

    @timedrole.command(name="add")
    async def add_role(self, ctx: RedContext, member: discord.Member, duration: FutureTime(strict=True),
                       *roles: discord.Role):
        """Add one or more roles to a user for a set amount of time.

        Examples for duration: `5d`, `1mo`, `1y2mo3w4d5m6s`

        Abbreviations: `s` for seconds, `m` for minutes, `h` for hours, `d` for days, `w` for weeks,
        `mo` for months, `y` for years. Any longer abbreviation is accepted. `m` assumes minutes instead of months.

        One month is counted as 30 days, and one year is counted as 365 days. All invalid abbreviations are ignored.

        Maximum duration for a timed role is two years. Expired timed roles are checked every 3 minutes."""
        if duration is None:
            await ctx.send_help()
            return
        roles = list(roles)
        if ctx.guild.default_role in roles:
            roles.remove(ctx.guild.default_role)
        if not roles:
            await ctx.send_help()
            return
        if any([role >= ctx.author.top_role for role in roles]):
            await ctx.send(warning("One or more of those roles is either your highest ranked role, "
                                   "or higher than your highest ranked role"))
            return
        if any([role >= ctx.guild.me.top_role for role in roles]):
            await ctx.send(warning("One or more of those roles is either my highest ranked role, "
                                   "or higher than my highest ranked role"))
            return
        try:
            await self.add_roles(member=member, duration=duration, granted_by=ctx.author, roles=roles)
        except discord.Forbidden:
            await ctx.send(warning("I failed to give one or more of those roles to the specified user"))
        except RuntimeError as e:
            await ctx.send(warning(str(e)))
        else:
            await ctx.tick()
            formatted_delta = td_format(duration)
            msg = "Successfully granted {0!s} to **{1!s}** for {2}".format(", ".join([bold(str(x)) for x in roles]),
                                                                           member, formatted_delta)
            await ctx.send(msg)

    @timedrole.command(name="expire", hidden=True)
    async def fake_expiry(self, ctx: RedContext, member: discord.Member, role: discord.Role = None):
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
        await ctx.send("Forcefully expired {} role{}".format(role.name if role else "all", "s" if not role else ""))

    @timedrole.command(name="fakejoin", hidden=True)
    @checks.is_owner()
    async def fake_join(self, ctx: RedContext, member: discord.Member):
        """Fake a member join event"""
        await self.on_member_join(member)
        await ctx.tick()

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
            for role in roles:
                await member.add_roles(role.role, reason="{} (role reapplied after member rejoin)".format(role.reason))
