from typing import Tuple

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import escape, bold
from redbot.core.i18n import Translator, cog_i18n

from cog_shared.swift_libs.time import td_format

_ = Translator("UInfo", __file__)


@cog_i18n(_)
class UInfo:
    """Yet another [p]userinfo variation"""

    __author__ = "odinair <odinair@odinair.xyz>"

    def __init__(self, bot: Red):
        self.bot = bot

    async def get_bot_role(self, member: discord.Member):
        if member.bot:
            return "\N{ROBOT FACE} Bot"

        if await self.bot.is_owner(member):
            return _("\N{HAMMER AND WRENCH} **Bot Owner**")

        if member.guild.owner.id == member.id:
            return _("\N{KEY} Server Owner")
        elif await self.bot.is_admin(member):
            return _("\N{HAMMER} Server Administrator")
        elif await self.bot.is_mod(member):
            return _("\N{SHIELD} Server Moderator")
        else:
            return _("\N{BUSTS IN SILHOUETTE} Server Member")

    @staticmethod
    def get_activity(member: discord.Member):
        if member.activity is None:
            return None

        game = None
        if member.activity.type == discord.ActivityType.playing:
            game = _("\N{VIDEO GAME} Playing **{}**").format(member.activity.name)
        elif member.activity.type == discord.ActivityType.streaming:
            game = _("\N{VIDEO CAMERA} Streaming **{}**").format(
                "[{0}]({0.url})".format(member.activity)
            )
        elif member.activity.type == discord.ActivityType.listening:
            game = _("\N{MUSICAL NOTE} Listening to **{}**").format(member.activity.name)
            if isinstance(member.activity, discord.Spotify):
                game = _(
                    "\N{MUSICAL NOTE} Listening to **{}** \N{EM DASH} **{}** on **Spotify**"
                ).format(
                    ", ".join(member.activity.artists), member.activity.title
                )
        elif member.activity.type == discord.ActivityType.watching:
            game = _("\N{FILM PROJECTOR} Watching **{}**").format(member.activity.name)

        return game

    @staticmethod
    def get_status(member: discord.Member) -> Tuple[str, str]:
        """This is a terrible way to handle i18n with status strings."""
        if member.status == discord.Status.online:
            return "\N{HIGH VOLTAGE SIGN}", _("Online")
        elif member.status == discord.Status.idle:
            return "\N{HIGH VOLTAGE SIGN}", _("Idle")
        elif member.status == discord.Status.dnd:
            return "\N{HIGH VOLTAGE SIGN}", _("Do Not Disturb")
        else:
            return "\N{SLEEPING SYMBOL}", _("Offline")

    @commands.command(aliases=["uinfo", "whois"])
    @commands.guild_only()
    async def user(self, ctx: commands.Context, *, user: discord.Member = None):
        """Displays your or a specified user's profile"""
        user = user or ctx.author
        member_number = sorted(ctx.guild.members, key=lambda m: m.joined_at).index(user) + 1

        since_created = td_format(user.created_at - ctx.message.created_at, append_str=True)
        since_joined = td_format(user.joined_at - ctx.message.created_at, append_str=True)

        colour = user.colour
        if colour == discord.Colour.default():
            colour = discord.Embed.Empty

        description = [" ".join(self.get_status(user)), await self.get_bot_role(user)]

        activity = self.get_activity(user)
        if activity is not None:
            description.append(activity)

        if user.nick:
            description.append(
                _("\N{LABEL} Nicknamed as {}").format(bold(escape(user.nick, formatting=True)))
            )

        description = "\n".join(description)

        embed = discord.Embed(title=str(user), colour=colour, description=description)
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text=_("Member #{} | User ID: {}").format(member_number, user.id))

        roles = ", ".join(
            reversed([str(x) for x in user.roles if not x.is_default()] or [_("None")])
        )
        embed.add_field(name=_("Server Roles"), value=roles, inline=False)

        embed.add_field(name=_("Joined Discord"), value=since_created, inline=False)
        embed.add_field(name=_("Joined Server"), value=since_joined, inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="avatar")
    @commands.guild_only()
    async def avatar(self, ctx: commands.Context, *, user: discord.Member = None):
        """Get the avatar of yourself or a specified user"""
        user = ctx.author if user is None else user
        embed = discord.Embed(colour=user.colour, title=_("{}'s avatar").format(str(user)))
        embed.set_image(url=user.avatar_url_as(static_format="png"))
        await ctx.send(embed=embed)
