import asyncio

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import warning, pagify, bold

from datetime import datetime, timedelta

from odinair_libs.formatting import td_format
from odinair_libs.converters import TimeDuration


class GuildRoles:
    def __init__(self, config: Config, guild: discord.Guild):
        self._config = config
        self.guild = guild

    @property
    def roles(self):
        return self.guild.roles

    async def all_temp_roles(self, show_hidden: bool = False, *members: discord.Member):
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
                    if not show_hidden and role.hidden:
                        continue
                    roles.append(role)
        return roles

    async def expired_roles(self, show_hidden: bool = False, *members: discord.Member):
        return [x for x in await self.all_temp_roles(show_hidden=show_hidden, *members) if x.has_expired]

    async def remove(self, member: discord.Member, role: discord.Role or int):
        async with self._config.member(member).roles() as temp_roles:
            for item in temp_roles:
                if item.get("role_id", None) == (role.id if isinstance(role, discord.Role) else role):
                    temp_roles.remove(item)


class TRole:
    def __init__(self, role: discord.Role, guild: GuildRoles, member: discord.Member, given_at: datetime, seconds: int,
                 granted_by: discord.Member, hidden: bool = False):
        self.member = member
        self.role = role
        self.guild = guild
        self.expiry_time = given_at + timedelta(seconds=seconds)
        self.granted_by = granted_by
        self.hidden = hidden

    @classmethod
    def from_data(cls, guild: GuildRoles, member: discord.Member, data: dict):
        role = discord.utils.get(guild.roles, id=data.get("role_id", None))
        if role is None:
            raise ValueError("Data does not contain a role ID, or the role was deleted")
        return cls(role=role, member=member, guild=guild, given_at=data.get("added_at"), seconds=data.get("duration"),
                   granted_by=guild.guild.get_member(data.get("granted_by")))

    def until_expires(self, as_string: bool=False):
        expiry_ts = self.expiry_time - datetime.utcnow()
        if as_string is False:
            return expiry_ts
        else:
            return td_format(expiry_ts) if expiry_ts > timedelta() else "Queued for removal"

    @property
    def has_expired(self):
        return self.role not in self.member.roles or self.expiry_time < datetime.utcnow()

    async def remove(self):
        await self.guild.remove(self.member, self.role)
        if self.role in self.member.roles:
            try:
                await self.member.remove_roles(self.role, reason="Timed role expired")
            except discord.Forbidden:
                pass


class TimedRole:
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=35235234, force_registration=True)
        self.config.register_member(roles=[])
        self.bot.loop.create_task(self.remove_expired_roles())

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
        guild_roles = GuildRoles(config=self.config, guild=ctx.guild)
        strings = []
        for member_id in members:
            member = ctx.guild.get_member(member_id)
            if not member:
                continue
            roles = await guild_roles.all_temp_roles(member)
            role_strs = []
            for role in roles:
                if role.hidden is True:
                    continue
                role_strs.append("**❯** Role: **{role!s}**\n"
                                 "      Granted by: **{granted_by!s}**\n"
                                 "      Expires in: **{duration}**".format(role=role.role,
                                                                           granted_by=role.granted_by,
                                                                           duration=role.until_expires(True)))
            strings.append("Member **{0!s}**:\n{1}".format(member, "\n".join(role_strs)))
        if not strings:
            await ctx.send(warning("There's no members in this server with any timed roles"
                                   if not members else "None of those members have active timed roles"))
        await ctx.send_interactive(pagify("\n\n".join(strings), escape_mass_mentions=True))

    async def add_roles(self, member: discord.Member, granted_by: discord.Member, duration: timedelta,
                        reason: str = None, hidden: bool = False, *roles: discord.Role):
        """Adds roles to a member.

        Parameters
        -----------

            member: discord.Member

                The member to add the roles to

            granted_by: discord.Member

                The member who granted the user the role(s)

            duration: timedelta

                How long to give the user the role for

            reason: str

                Optional reason that displays in the audit log

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
        elif duration is False:
            raise RuntimeError("That's an invalid time format")

        now = datetime.utcnow()
        duration = duration.total_seconds()

        await member.add_roles(*roles,
                               reason="Timed role granted by {0!s}".format(granted_by)
                               if reason is None else reason)

        async with self.config.member(member).roles() as tmp_roles:
            for role in roles:
                tmp_roles.append({"role_id": role.id,
                                  "added_at": now,
                                  "duration": duration,
                                  "granted_by": granted_by.id,
                                  "hidden": hidden})

    @timedrole.command(name="multiple")
    async def add_multiple(self, ctx: RedContext, member: discord.Member,
                           duration: TimeDuration, *roles: discord.Role):
        """Add multiple roles to a user at once

        See `[p]timedrole add` for help on `duration`

        If a role has spaces in its name, wrap it in double quotes."""
        if duration is None:
            duration = await TimeDuration().convert(ctx, argument='1mo')
        elif duration is False:
            await ctx.send_help()
            return
        roles = list(roles)
        if ctx.guild.default_role in roles:
            roles.remove(ctx.guild.default_role)
        if not roles:
            await ctx.send_help()
            return
        try:
            await self.add_roles(member, ctx.author, duration, reason=None, hidden=False, *roles)
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

    @timedrole.command(name="add")
    async def add_role(self, ctx: RedContext, member: discord.Member, role: discord.Role,
                       duration: TimeDuration = None):
        """Add a role to a user for a set amount of time.

        Examples for duration: `5d`, `1mo`, `1y2mo3w4d5m6s`

        Abbreviations: `s` for seconds, `m` for minutes, `h` for hours, `d` for days, `w` for weeks,
        `mo` for months, `y` for years. Any longer abbreviation is accepted. `m` assumes minutes instead of months.

        One month is counted as 30 days, and one year is counted as 365 days. All invalid abbreviations are ignored.

        Maximum duration for a timed role is two years. Expired timed roles are checked every 5 minutes."""
        if duration is None:
            duration = await TimeDuration().convert(ctx, argument='1mo')
        elif duration is False:
            await ctx.send_help()
            return
        try:
            await self.add_roles(member, ctx.author, duration, None, False, role)
        except discord.Forbidden:
            await ctx.send(warning("I failed to give one or more of those roles to the specified user"))
        except RuntimeError as e:
            await ctx.send(warning(str(e)))
        else:
            await ctx.tick()
            formatted_delta = td_format(duration)
            msg = "Successfully granted {0!s} to **{1!s}** for {2}".format(bold(str(role)), member, formatted_delta)
            await ctx.send(msg)

    async def remove_expired_roles(self):
        while self == self.bot.get_cog(self.__class__.__name__):
            for guild in self.bot.guilds:
                guild = GuildRoles(config=self.config, guild=guild)
                expired = await guild.expired_roles()
                for role in expired:
                    await role.remove()
            await asyncio.sleep(300)
