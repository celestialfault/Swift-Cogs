from asyncio import sleep
from typing import Sequence
from datetime import datetime

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks
from redbot.core.i18n import CogI18n
from redbot.core.utils.chat_formatting import warning, bold

from timedrole.role import TempRole

from cog_shared.odinair_libs.formatting import chunks, tick
from cog_shared.odinair_libs.commands import fmt
from cog_shared.odinair_libs.time import FutureTime, td_format
from cog_shared.odinair_libs.menus import PaginateMenu

_ = CogI18n("TimedRole", __file__)


class TimedRole:
    """Give users roles for a set amount of time"""

    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = "2.0.0"

    def __init__(self, bot: Red):
        self.bot = bot
        TempRole.bot = self.bot
        self._role_task = self.bot.loop.create_task(self._handle_roles())

    def __unload(self):
        self._role_task.cancel()

    async def _handle_roles(self):
        await self.bot.wait_until_ready()
        await sleep(2)
        while True:
            roles = await TempRole.all_roles()
            for role in roles:
                if role.role not in role.member.roles:
                    await role.apply_role(reason=_("Re-applying missing timed role"))
            await sleep(60)

    # noinspection PyMethodMayBeStatic
    async def on_member_join(self, member: discord.Member):
        roles = await TempRole.all_roles(member.guild, member)
        for role in roles:
            await role.apply_role(reason=_("Re-applying timed role after member re-join"))

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def timedrole(self, ctx: RedContext):
        """Timed role management"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @timedrole.command(name="list")
    async def timedrole_list(self, ctx: RedContext):
        """List all active timed roles"""
        roles = list(chunks(await TempRole.all_roles(guild=ctx.guild), 4))
        if not roles:
            await ctx.send(warning(_("This guild has no currently active timed roles")))
            return

        def convert(roles_: Sequence[TempRole], page_id: int):
            for role in roles_:
                rid = ((page_id * 4) + roles_.index(role)) + 1

                yield _(
                    "**❯** Timed role **#{id}**\n"
                    "**Member** \N{EM DASH} {member}\n"
                    "**Role** \N{EM DASH} {role}\n"
                    "**Given by** \N{EM DASH} {given_by} \N{EM DASH} {given_at}\n"
                    "**Reason** \N{EM DASH} {reason}\n"
                    "**Expires** \N{EM DASH} {expires}\n"
                    "**Total duration** \N{EM DASH} {duration}"
                ).format(
                    id=rid, member=role.member.mention, role=role.role.mention,
                    reason=role.reason or _("No reason specified"),
                    given_by=getattr(role.added_by, "mention", _("An unknown member")),
                    given_at=td_format(role.added_at - datetime.utcnow()),
                    expires=td_format(role.expires_at - datetime.utcnow(), append_str=True),
                    duration=td_format(role.expires_at - role.added_at)
                )

        def page_convert(x, page, pages):
            return (
                discord.Embed(description="\n\n".join(list(convert(x, page))), colour=ctx.me.colour)
                .set_footer(text=_("Page {}/{}").format(page + 1, pages))
                .set_author(name=_("Timed Roles"), icon_url=ctx.guild.icon_url)
            )

        async with PaginateMenu(ctx, pages=roles, converter=page_convert, actions={}):
            pass

    @timedrole.command(name="add")
    async def timedrole_add(self, ctx: RedContext, member: discord.Member,
                            duration: FutureTime.converter(strict=True, min_duration=5*60),
                            *roles: discord.Role):
        """Add one or more roles to a user for a set amount of time.

        You can give a user up to 10 roles at once.

        Examples for duration: `5d`, `1mo`, `1y2mo3w4d5m6s`

        Abbreviations: `s` for seconds, `m` for minutes, `h` for hours, `d` for days, `w` for weeks,
        `mo` for months, `y` for years. Any longer abbreviation is accepted. `m` assumes minutes instead of months.

        One month is counted as 30 days, and one year is counted as 365 days. All invalid abbreviations are ignored.

        Minimum duration for a timed role is five minutes; maximum duration is two years.

        Any roles that are above the author or the bots top role are silently ignored.
        """
        roles = [x for x in roles if not any([x in member.roles, x >= ctx.author.top_role, x >= ctx.me.top_role])]
        if any([not roles, len(roles) > 10]):
            await ctx.send_help()
            return

        for role in roles:
            role = await TempRole.create(member, role=role, duration=duration, added_by=ctx.author)
            await role.apply_role()

        await fmt(ctx, tick(_("Added role(s) {roles} to member **{member}** for **{duration}** successfully.")),
                  roles=", ".join([bold(x.name) for x in roles]), member=member, duration=duration.format())

    @timedrole.command(name="remove")
    async def timedrole_expire(self, ctx: RedContext, member: discord.Member, *roles: discord.Role):
        """Remove one or all active timed roles from a member"""
        mroles = await TempRole.all_roles(ctx.guild, member)
        for r in mroles:
            if not roles or r.role in roles:
                await r.remove_role(reason=_("Role removed by {}").format(ctx.author))
        if not roles:
            await ctx.send(_("Removed all timed roles from member **{}**").format(member))
        else:
            await ctx.send(_("Removed roles {} from member **{}**").format(
                ", ".join(bold(str(x)) for x in roles), member))
