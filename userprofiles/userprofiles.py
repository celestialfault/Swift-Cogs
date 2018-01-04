import asyncio
from datetime import timedelta

import discord
from discord.ext import commands

from redbot.core import Config, RedContext
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import escape

from urllib.parse import urlparse


class UserProfile:
    defaults_user = {
        "age": None,
        "about": None,
        "country": None,
        "gender": None
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=656542234, force_registration=True)
        self.config.register_user(**self.defaults_user)

    async def get_role(self, member: discord.Member):
        if member.bot:
            return None

        _msg = ""
        if await self.bot.is_owner(member):
            _msg = "\N{HAMMER AND WRENCH} **Bot Owner**\n"

        if member.guild.owner.id == member.id:
            _msg += "\N{KEY} Guild Owner"
        elif await self.bot.is_admin(member):
            _msg += "\N{HAMMER} Server Administrator"
        elif await self.bot.is_mod(member):
            _msg += "\N{SHIELD} Server Moderator"
        else:
            _msg += "\N{BUSTS IN SILHOUETTE} Server Member"
        return _msg

    @commands.command()
    @commands.guild_only()
    async def user(self, ctx: RedContext, *, user: discord.Member = None):
        """Displays your or a specified user's profile"""
        user = user if user else ctx.author
        _user_data = self.config.user(user)
        user_info = {
            "about": await _user_data.about(),
            "country": await _user_data.country(),
            "age": await _user_data.age(),
            "gender": await _user_data.gender()
        }

        # Role list
        roles = reversed([escape(x.name, formatting=True) for x in user.roles if x.name != "@everyone"])
        roles = ", ".join(roles) if roles else "None"

        # Game display
        status = str(user.status).replace("_", " ").replace("dnd", "do not disturb").title()
        game = "nothing" if not user.game else str(user.game)
        game_type = "\N{VIDEO GAME} Playing"
        if user.game is None:
            pass
        elif user.game.type == 1:
            game_type = "\N{VIDEO CAMERA} Streaming"
            game = "[{}]({})".format(user.game, user.game.url)
        elif user.game.type == 2:
            game_type = "\N{MUSICAL NOTE} Listening to"
        elif user.game.type == 3:
            game_type = "\N{FILM PROJECTOR} Watching"

        # I couldn't find a better status-like emoji okay
        _status = "\N{EARTH GLOBE AMERICAS} {status}{game_status}{nick}"
        game_status = ""
        nick_status = ""
        if user.game:
            game_status = "\n{type} **{game}**".format(type=game_type, game=game)
        if user.nick:
            nick_status = "\n\N{LABEL} Nicknamed as **{}**".format(escape(user.nick, formatting=True))
        status = _status.format(status=status, game_status=game_status, nick=nick_status)

        # Created / join dates
        since_joined = td_format(ctx.message.created_at - user.joined_at)
        since_created = td_format(ctx.message.created_at - user.created_at)

        # Member join position
        member_number = sorted(ctx.guild.members,
                               key=lambda m: m.joined_at).index(user) + 1

        embed = discord.Embed(title=str(user), colour=user.colour, description=status)
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text="Member #{} | User ID: {}".format(member_number, user.id))

        bot_roles = await self.get_role(user)
        if bot_roles:
            embed.add_field(name="Bot Roles", value=bot_roles, inline=False)
        embed.add_field(name="Guild Roles", value=roles, inline=False)

        embed.add_field(name="Joined Discord", value="{} ago".format(since_created), inline=False)
        embed.add_field(name="Joined Guild", value="{} ago".format(since_joined), inline=False)
        if user_info.get("country", None) is not None:
            embed.add_field(name="Country", value=str(user_info.get("country")))
        if user_info.get("age", None) is not None:
            embed.add_field(name="Age", value=str(user_info.get("age")))
        if user_info.get("gender", None):
            embed.add_field(name="Gender", value=user_info.get("gender"))
        if user_info.get("about", None):
            embed.add_field(name="About Me", value=user_info.get("about"), inline=False)
        await ctx.send(embed=embed)

    @commands.group(name="profile")
    async def userset(self, ctx: RedContext):
        """Change your user profile settings"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @userset.command(name="about")
    async def _user_about(self, ctx: RedContext, *, about: str = ""):
        """Sets your About Me message, maximum of 600 characters

        Any text beyond 600 characters is trimmed off"""
        about = escape(about, mass_mentions=True)[:600]
        await self.config.user(ctx.author).about.set(about)
        if about is None:
            await ctx.send("\N{WHITE HEAVY CHECK MARK} Cleared your about me", delete_after=15)
        else:
            await ctx.send("\N{WHITE HEAVY CHECK MARK} Set your about me to:\n```\n{}\n```".format(about),
                           delete_after=15)

    @userset.command(name="age")
    async def _user_age(self, ctx: RedContext, age: int = None):
        """Sets your age"""
        await self.config.user(ctx.author).age.set(age)
        if age is None:
            await ctx.send("\N{WHITE HEAVY CHECK MARK} Cleared your age", delete_after=15)
        else:
            await ctx.send("\N{WHITE HEAVY CHECK MARK} Set your age to:\n```\n{}\n```".format(age), delete_after=15)

    @userset.command(name="country")
    async def _user_country(self, ctx: RedContext, *, country: str = ""):
        """Set the country you reside in

        Any text beyond 75 characters is trimmed off"""
        country = escape(country, mass_mentions=True)[:75]
        await self.config.user(ctx.author).country.set(country)
        if country is None:
            await ctx.send("\N{WHITE HEAVY CHECK MARK} Cleared your country", delete_after=15)
        else:
            await ctx.send("\N{WHITE HEAVY CHECK MARK} Set your country to:\n```\n{}\n```".format(country),
                           delete_after=15)

    @userset.command(name="gender")
    async def _user_gender(self, ctx: RedContext, *, gender: str = ""):
        """Sets your gender

        Any text beyond 50 characters is trimmed off"""
        gender = escape(gender, mass_mentions=True)[:50]
        await self.config.user(ctx.author).gender.set(gender)
        if gender is None:
            await ctx.send("\N{WHITE HEAVY CHECK MARK} Cleared your gender", delete_after=15)
        else:
            await ctx.send("\N{WHITE HEAVY CHECK MARK} Set your gender to:\n```\n{}\n```".format(gender),
                           delete_after=15)

    @userset.command(name="reset")
    async def _user_reset(self, ctx: RedContext, *, user: discord.User = None):
        """Resets your user profile.

        If a user is passed in the command and the command issuer is the bot owner or a co-owner,
        this resets the specified user's profile instead"""
        if not user:
            user = ctx.author
        if user and not await self.bot.is_owner(ctx.author):
            user = ctx.author
        descriptor = "your"
        if user.id != ctx.author.id:
            descriptor = "**{}**'s".format(str(user))

        embed = discord.Embed(description="Are you sure you want to reset {} profile?\n\n"
                                          "**This is irreversible**!\n\n"
                                          "**Click \N{WHITE HEAVY CHECK MARK} to confirm or "
                                          "\N{REGIONAL INDICATOR SYMBOL LETTER X} to cancel**"
                                          "".format(descriptor),
                              colour=discord.Colour.red())
        check_msg = await ctx.send(embed=embed)
        await check_msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await check_msg.add_reaction("\N{REGIONAL INDICATOR SYMBOL LETTER X}")

        def check(_reaction, _user):
            msg = _reaction.message
            if msg.id != check_msg.id or _user.id != user.id:
                return False
            expected = ["\N{WHITE HEAVY CHECK MARK}", "\N{REGIONAL INDICATOR SYMBOL LETTER X}"]
            return str(_reaction.emoji) in expected

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("❌ Operation cancelled.", delete_after=15)
        else:
            if str(reaction.emoji) == "\N{REGIONAL INDICATOR SYMBOL LETTER X}":
                await ctx.send("❌ Operation cancelled.", delete_after=15)
                return await check_msg.delete()
            await self.config.user(user).set(self.defaults_user)
            await ctx.send("\N{WHITE HEAVY CHECK MARK} Profile reset.", delete_after=15)
        await check_msg.delete()


async def is_url(url: str) -> bool:
    if not url:  # Allow url to be None
        return True
    url = urlparse(url)
    return url.scheme and url.netloc


# ~~stolen~~ borrowed from StackOverflow
# https://stackoverflow.com/a/13756038
def td_format(td_object: timedelta) -> str:
    seconds = int(td_object.total_seconds())
    periods = [
        ('year', 60 * 60 * 24 * 365),
        ('month', 60 * 60 * 24 * 30),
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value == 1:
                strings.append("%s %s" % (period_value, period_name))
            else:
                strings.append("%s %ss" % (period_value, period_name))

    return ", ".join(strings)
