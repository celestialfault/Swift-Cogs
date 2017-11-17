import asyncio

import discord
from discord.ext import commands
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import escape
from urllib.parse import urlparse


class UserProfile:
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=656542234, force_registration=True)
        defaults_user = {
            "age": None,
            "about": None,
            "country": None,
            "gender": None
        }
        self.config.register_user(**defaults_user)

    async def get_role(self, member: discord.Member):
        _msg = ""
        if member.bot:
            _msg += "🤖 **Bot**\n"
        elif await self.bot.is_owner(member):
            _msg = "🛠 **Bot Owner**\n"

        if await self.bot.is_admin(member):
            _msg += "🔨 Server Administrator"
        elif await self.bot.is_mod(member):
            _msg += "🛡 Server Moderator"
        else:
            _msg += "👥 Server Member"
        return _msg

    @commands.command(name="user")
    async def _user(self, ctx: commands.Context, user: discord.Member = None):
        """
        Displays your or a specified user's profile
        """
        user = ctx.author if not user else user
        userinfo = self.config.user(user)
        userinfo = {
            "about": await userinfo.about(),
            "country": await userinfo.country(),
            "age": await userinfo.age(),
            "gender": await userinfo.gender()
        }
        roles = [x.name for x in user.roles if x.name != "@everyone"]
        if roles:
            roles = ", ".join(roles)
        else:
            roles = "None"

        status = user_status(user)
        game = "Nothing" if not user.game else str(user.game)
        game_type = "Playing"
        if user.game is None:
            pass
        elif user.game.type == 1:
            game_type = "Streaming"
            game = "[{}]({})".format(user.game, user.game.url)
        elif user.game.type == 2:
            game_type = "Listening to"
        elif user.game.type == 3:
            game_type = "Watching"

        joined_at = user.joined_at
        since_created = (ctx.message.created_at - user.created_at).days
        since_joined = (ctx.message.created_at - joined_at).days
        user_joined = joined_at.strftime("%d %b %Y %H:%M:%S")
        user_created = user.created_at.strftime("%d %b %Y %H:%M:%S")
        member_number = sorted(ctx.guild.members,
                               key=lambda m: m.joined_at).index(user) + 1

        embed = discord.Embed(color=user.colour)
        embed.set_author(name="Profile for {}".format(user.display_name), icon_url=user.avatar_url)

        embed.add_field(name="Status", value=status)
        embed.add_field(name=game_type, value=game)
        embed.add_field(name=u"\u2063", value=u"\u2063")

        embed.add_field(name="Bot Roles", value=await self.get_role(user))
        embed.add_field(name="Joined Discord", value="{}\n({} days ago)".format(user_created, since_created))
        embed.add_field(name="Joined Server", value="{}\n({} days ago)".format(user_joined, since_joined))

        embed.add_field(name="Roles", value=roles, inline=False)
        if userinfo["country"]:
            embed.add_field(name="Country", value=userinfo["country"])
        if userinfo["age"]:
            embed.add_field(name="Age", value=str(userinfo["age"]))
        if userinfo["gender"]:
            embed.add_field(name="Gender", value=userinfo["gender"])
        if userinfo["about"]:
            embed.add_field(name="About Me", value=userinfo["about"], inline=False)

        embed.set_footer(text="Member #{} | User ID: {}".format(member_number, user.id))

        await ctx.send(embed=embed)

    @commands.group(name="userset")
    async def userset(self, ctx: commands.Context):
        """
        Change your user profile settings
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @userset.command(name="about")
    async def _user_about(self, ctx: commands.Context, *, about: str = None):
        """
        Sets your About Me message, maximum of 500 characters

        Any text beyond 500 characters is trimmed off
        """
        about = escape(about, mass_mentions=True)[:500]
        await self.config.user(ctx.author).about.set(about)
        if about is None:
            await ctx.send("✅ Cleared your about me", delete_after=15)
        else:
            await ctx.send("✅ Set your about me to:\n```\n{}\n```".format(about), delete_after=15)

    @userset.command(name="age")
    async def _user_age(self, ctx: commands.Context, age: int = None):
        """
        Sets your age
        """
        if age and age > 110:
            return await ctx.send(":thinking: I'm finding it hard to believe you're actually that old.")
        if age and age < 0:
            return await ctx.send(":thinking: Something seems off here.")
        await self.config.user(ctx.author).age.set(age)
        if age is None:
            await ctx.send("✅ Cleared your age", delete_after=15)
        else:
            await ctx.send("✅ Set your age to:\n```\n{}\n```".format(age), delete_after=15)

    @userset.command(name="country")
    async def _user_country(self, ctx: commands.Context, *, country: str = None):
        """
        Set the country you reside in

        Any text beyond 100 characters is trimmed off
        """
        country = escape(country, mass_mentions=True)[:100]
        await self.config.user(ctx.author).country.set(country)
        if country is None:
            await ctx.send("✅ Cleared your country", delete_after=15)
        else:
            await ctx.send("✅ Set your country to:\n```\n{}\n```".format(country), delete_after=15)

    @userset.command(name="gender")
    async def _user_gender(self, ctx: commands.Context, *, gender: str = None):
        """
        Sets your gender
        """
        gender = escape(gender, mass_mentions=True)[:50]
        await self.config.user(ctx.author).gender.set(gender)
        if gender is None:
            await ctx.send("✅ Cleared your gender", delete_after=15)
        else:
            await ctx.send("✅ Set your gender to:\n```\n{}\n```".format(gender), delete_after=15)

    @userset.command(name="reset")
    async def _user_reset(self, ctx: commands.Context, user: discord.User = None):
        """
        Resets your user profile.

        If a user is passed in the command and the command issuer is the bot owner, this resets the specified user's profile
        """
        if not (user and await self.bot.is_owner(ctx.author)):
            user = ctx.author
        descriptor = "your"
        if user.id != ctx.author.id:
            descriptor = "**{}**'s".format(str(user))

        embed = discord.Embed(description="Are you sure you want to reset " + descriptor + " profile?"
                                          "\n\n**This is irreversible**!",
                              colour=discord.Colour.red())
        check_msg = await ctx.send(embed=embed)
        await check_msg.add_reaction("✅")
        await check_msg.add_reaction("🇽")
        try:
            reaction, user = await self.bot.wait_for("reaction_add",
                                                     # I don't know how this works either.
                                                     check=lambda r, u: u.id == ctx.author.id and (
                                                        not (not (str(r.emoji) == "🇽") and not (str(r.emoji) == "✅"))),
                                                     timeout=60)
        except asyncio.TimeoutError:
            await ctx.send(":x: Operation cancelled.", delete_after=15)
            return await check_msg.delete()
        if str(reaction.emoji) == "🇽":
            await ctx.send(":x: Operation cancelled.", delete_after=15)
            return await check_msg.delete()
        await self.config.user(user).clear()
        await ctx.send("✅ Profile reset.", delete_after=15)
        await check_msg.delete()


async def is_url(url: str) -> bool:
    if not url:  # Allow url to be None
        return True
    url = urlparse(url)
    return url.scheme and url.netloc


def user_status(user: discord.Member) -> str:
    if user.status == discord.Status.online:
        return "Online"
    elif user.status == discord.Status.idle:
        return "Idle"
    elif user.status == discord.Status.do_not_disturb:
        return "Do Not Disturb"
    elif user.status == discord.Status.offline:
        return "Offline"
    else:
        return "Unknown status"
