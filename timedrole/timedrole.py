import asyncio

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import warning, pagify

from collections import OrderedDict
import re

from datetime import datetime, timedelta


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
        self.bot.loop.create_task(self.check_role_expirations())

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def timedrole(self, ctx: RedContext):
        """Timed role management"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @timedrole.command(name="list")
    async def list_roles(self, ctx: RedContext, *, member: discord.Member = None):
        """List all members with temporary roles"""
        if not member:
            members = await self.config.all_members(ctx.guild)
        else:
            members = {member.id: await self.config.member(member)()}
        members = {x: members[x] for x in members if members[x] and members[x]["roles"]}
        if not len(members):
            await ctx.send(warning("There's no timed roles currently on this server" if not member
                                   else "That member has no timed roles"))
            return
        strings = []
        for member_id in members:
            member = ctx.guild.get_member(member_id)
            if not member:
                continue
            roles = []
            for role in members[member_id]["roles"]:
                expires_at = role["added_at"] + timedelta(seconds=role["duration"])
                # noinspection PyTypeChecker
                duration_left = expires_at - datetime.utcnow()
                roles.append(
                    "**❯** Role **{role!s}**\n      Granted by: **{granted_by!s}**\n      Expires in: **{duration}**"
                    .format(role=discord.utils.get(ctx.guild.roles, id=role["role_id"]),
                            granted_by=ctx.guild.get_member(role["granted_by"]),
                            duration=self.td_format(duration_left) if duration_left > timedelta()
                            else "Queued for removal"))
            msg = "Member **{0!s}**:\n{1}".format(member, "\n".join(roles))
            strings.append(msg)
        await ctx.send_interactive(pagify("\n\n".join(strings), escape_mass_mentions=True))

    @timedrole.command(name="add")
    async def add_role(self, ctx: RedContext, member: discord.Member, role: discord.Role, duration: str = "1mo"):
        """Add a role to a user for a set amount of time.

        Examples for duration: `5d`, `1mo`, `1y2mo3w4d5m6s`

        Abbreviations: `s` for seconds, `m` for minutes, `h` for hours, `d` for days, `w` for weeks,
        `mo` for months, `y` for years. Any longer abbreviation is accepted. `m` assumes minutes instead of months.

        One month is counted as 30 days, and one year is counted as 365 days. All invalid abbreviations are ignored.

        Maximum duration for a timed role is two years. Expired timed roles are checked every 5 minutes."""
        if role in member.roles:
            await ctx.send(warning("That user already has that role"))
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
        delta = timedelta(seconds=duration)
        try:
            await member.add_roles(role, reason="Timed role granted by {0!s}".format(ctx.author))
        except discord.Forbidden:
            await ctx.send(warning("I'm not allowed to give that role to users"))
        except discord.HTTPException:
            await ctx.send(warning("I failed to give that role to the specified user"))
        else:
            await ctx.tick()
            formatted_delta = self.td_format(delta)
            msg = "Successfully granted **{0!s}** to **{1!s}** for {2}".format(role, member, formatted_delta)
            await ctx.send(msg)
        async with self.config.member(member).roles() as tmp_roles:
            tmp_roles.append({"role_id": role.id,
                              "added_at": now,
                              "duration": duration,
                              "granted_by": ctx.author.id})

    async def check_role_expirations(self):
        while self == self.bot.get_cog(self.__class__.__name__):
            for guild in self.bot.guilds:
                members = await self.config.all_members(guild)
                for uid in members:
                    member = guild.get_member(uid)
                    if not member:
                        continue
                    async with self.config.member(member).roles() as temp_roles:
                        for item in temp_roles:
                            index = temp_roles.index(item)
                            role_id = item["role_id"]
                            role = discord.utils.get(guild.roles, id=role_id)
                            expiry = item["added_at"] + timedelta(seconds=item["duration"])
                            if not role or role not in member.roles:
                                temp_roles.pop(index)
                            elif datetime.utcnow() > expiry:
                                temp_roles.pop(index)
                                try:
                                    await member.remove_roles(role, reason="Timed role expired")
                                except (discord.Forbidden, discord.HTTPException):
                                    pass
            await asyncio.sleep(300)  # Check once every 5 minutes

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
