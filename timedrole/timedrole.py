import asyncio

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import warning, pagify, bold

from collections import OrderedDict
import re

from datetime import datetime, timedelta


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

    async def expired_roles(self, *members: discord.Member):
        return [x for x in await self.all_temp_roles(*members) if x.has_expired]

    async def remove(self, member: discord.Member, role: discord.Role or int):
        async with self._config.member(member).roles() as temp_roles:
            for item in temp_roles:
                if item.get("role_id", None) == (role.id if isinstance(role, discord.Role) else role):
                    temp_roles.remove(item)


class TRole:
    def __init__(self, role: discord.Role, guild: GuildRoles, member: discord.Member, given_at: datetime, seconds: int,
                 granted_by: discord.Member):
        self.member = member
        self.role = role
        self.guild = guild
        self.expiry_time = given_at + timedelta(seconds=seconds)
        self.granted_by = granted_by

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
            return TimedRole.td_format(expiry_ts) if expiry_ts > timedelta() else "Queued for removal"

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
    # The following, including `get_seconds`, is taken from ZeLarpMaster's Reminders cog:
    # https://github.com/ZeLarpMaster/ZeCogs/blob/master/reminder/reminder.py
    # Only changes made have been to make the parsed times more consistent with timedelta objects
    TIME_AMNT_REGEX = re.compile("([1-9][0-9]*)([a-z]+)", re.IGNORECASE)
    TIME_QUANTITIES = OrderedDict([("seconds", 1), ("minutes", 60),
                                   ("hours", timedelta(hours=1).total_seconds()),
                                   ("days", timedelta(days=1).total_seconds()),
                                   ("weeks", timedelta(days=7).total_seconds()),
                                   ("months", timedelta(days=30).total_seconds()),
                                   ("years", timedelta(days=365).total_seconds())])
    MAX_SECONDS = TIME_QUANTITIES["years"] * 2

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
        member_ids = [x.id for x in members]
        members = await self.config.all_members(ctx.guild)
        members = {uid: members[uid] for uid in members if not len(member_ids) or uid in member_ids}
        members = {x: members[x] for x in members if members[x] and members[x]["roles"]}
        if not len(members):
            await ctx.send(warning("There's no timed roles currently on this server" if not member_ids
                                   else "That member has no timed roles"))
            return
        guild_roles = GuildRoles(config=self.config, guild=ctx.guild)
        strings = []
        for member_id in members:
            member = ctx.guild.get_member(member_id)
            if not member:
                continue
            roles = await guild_roles.all_temp_roles(member)
            role_strs = []
            for role in roles:
                role_strs.append("**❯** Role: **{role!s}**\n"
                                 "      Granted by: **{granted_by!s}**\n"
                                 "      Expires in: **{duration}**".format(role=role.role,
                                                                           granted_by=role.granted_by,
                                                                           duration=role.until_expires(True)))
            strings.append("Member **{0!s}**:\n{1}".format(member, "\n".join(role_strs)))
        await ctx.send_interactive(pagify("\n\n".join(strings), escape_mass_mentions=True))

    async def add_roles(self, ctx: RedContext, member: discord.Member,
                        duration: str, *roles: discord.Role):
        roles = list(roles)
        try:
            roles.remove(ctx.guild.default_role)
        except ValueError:
            pass
        if len(roles) == 0:
            await ctx.send_help()
            return
        for role in roles:
            if role in member.roles:
                await ctx.send(warning("That user already has the {0!s} role".format(role)))
                return
        now = datetime.utcnow()
        duration = self.get_seconds(duration)
        if not duration:
            await ctx.send(warning("That's an invalid time format."))
            return
        elif duration > self.MAX_SECONDS:
            await ctx.send(warning("The maximum timed role duration is {}".format(
                self.td_format(timedelta(seconds=self.MAX_SECONDS)))))
            return
        try:
            await member.add_roles(*roles, reason="Timed role granted by {0!s}".format(ctx.author))
        except discord.Forbidden:
            await ctx.send(warning("I'm not allowed to give one or more of those roles to the specified user"))
        except discord.HTTPException:
            await ctx.send(warning("I failed to give one or more of those roles to the specified user"))
        else:
            await ctx.tick()
            formatted_delta = self.td_format(timedelta(seconds=duration))
            msg = "Successfully granted {0!s} to **{1!s}** for {2}".format(", ".join([bold(str(x)) for x in roles]),
                                                                           member, formatted_delta)
            await ctx.send(msg)
        async with self.config.member(member).roles() as tmp_roles:
            for role in roles:
                tmp_roles.append({"role_id": role.id,
                                  "added_at": now,
                                  "duration": duration,
                                  "granted_by": ctx.author.id})

    @timedrole.command(name="multiple")
    async def add_multiple(self, ctx: RedContext, member: discord.Member, duration: str, *roles: discord.Role):
        """Add multiple roles to a user at once

        See `[p]timedrole add` for help on `duration`

        If a role has spaces in its name, wrap it in double quotes."""
        await self.add_roles(ctx, member, duration, *roles)

    @timedrole.command(name="add")
    async def add_role(self, ctx: RedContext, member: discord.Member, role: discord.Role, duration: str = "1mo"):
        """Add a role to a user for a set amount of time.

        Examples for duration: `5d`, `1mo`, `1y2mo3w4d5m6s`

        Abbreviations: `s` for seconds, `m` for minutes, `h` for hours, `d` for days, `w` for weeks,
        `mo` for months, `y` for years. Any longer abbreviation is accepted. `m` assumes minutes instead of months.

        One month is counted as 30 days, and one year is counted as 365 days. All invalid abbreviations are ignored.

        Maximum duration for a timed role is two years. Expired timed roles are checked every 2 minutes."""
        await self.add_roles(ctx, member, duration, role)

    async def remove_expired_roles(self):
        while self == self.bot.get_cog(self.__class__.__name__):
            for guild in self.bot.guilds:
                guild = GuildRoles(config=self.config, guild=guild)
                expired = await guild.expired_roles()
                for role in expired:
                    await role.remove()
            await asyncio.sleep(300)

    # originally from ZeLarpMaster's Reminders cog
    def get_seconds(self, time):
        """Returns the amount of converted time or None if invalid"""
        seconds = 0
        for time_match in self.TIME_AMNT_REGEX.finditer(time):
            time_amnt = int(time_match.group(1))
            time_abbrev = time_match.group(2)
            time_quantity = discord.utils.find(lambda t: t[0].startswith(time_abbrev), self.TIME_QUANTITIES.items())
            if time_quantity is not None:
                seconds += time_amnt * time_quantity[1]
        return None if seconds == 0 else seconds

    # originally from StackOverflow with modifications made
    # https://stackoverflow.com/a/13756038
    @staticmethod
    def td_format(td_object: timedelta, short_format: bool = False, as_string: bool = True) -> str:
        seconds = int(td_object.total_seconds())
        if seconds < 0:  # Remove negative signs from numbers
            seconds = int(str(seconds)[1:])
        elif seconds == 0:  # Properly handle timedelta objects with no time
            return "0 seconds" if not short_format else "0s"
        periods = [
            ('year', 60 * 60 * 24 * 365), ('month', 60 * 60 * 24 * 30),
            ('day', 60 * 60 * 24), ('hour', 60 * 60), ('minute', 60), ('second', 1)]
        if short_format is True:
            periods = [
                ('y', 60 * 60 * 24 * 365), ('mo', 60 * 60 * 24 * 30),
                ('d', 60 * 60 * 24), ('h', 60 * 60), ('m', 60), ('s', 1)]

        strings = []
        for period_name, period_seconds in periods:
            if seconds >= period_seconds:
                period_value, seconds = divmod(seconds, period_seconds)
                if short_format:
                    strings.append("%s%s" % (period_value, period_name))
                elif period_value == 1:
                    strings.append("%s %s" % (period_value, period_name))
                else:
                    strings.append("%s %ss" % (period_value, period_name))

        return ", ".join(strings) if as_string is True else strings
