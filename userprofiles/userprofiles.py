import asyncio

import discord
from discord.ext import commands

from redbot.core import Config
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

    async def get_role(self, member: discord.Member, spaces: int=0):
        _msg = ""
        if member.bot:
            _msg += (" "*spaces) + "🤖 **Bot**\n"
        elif await self.bot.is_owner(member):
            _msg = (" "*spaces) + "🛠 **Bot Owner**\n"

        if await self.bot.is_admin(member):
            _msg += (" "*spaces) + "🔨 Server Administrator"
        elif await self.bot.is_mod(member):
            _msg += (" "*spaces) + "🛡 Server Moderator"
        else:
            _msg += (" "*spaces) + "👥 Server Member"
        return _msg

    @commands.command(name="user")
    async def _user(self, ctx: commands.Context, *, user: discord.Member=None):
        """
        Displays your or a specified user's profile
        """
        user = ctx.author if not user else user
        user_info = self.config.user(user)
        user_info = {
            "about": await user_info.about(),
            "country": await user_info.country(),
            "age": await user_info.age(),
            "gender": await user_info.gender()
        }

        # Role list
        roles = reversed([x.name for x in user.roles if x.name != "@everyone"])
        roles = ", ".join(roles) if roles else "None"

        # Game display
        status = user_status(user)
        game = "nothing" if not user.game else str(user.game)
        game_type = "playing"
        if user.game is None:
            pass
        elif user.game.type == 1:
            game_type = "streaming"
            game = "[{}]({})".format(user.game, user.game.url)
        elif user.game.type == 2:
            game_type = "listening to"
        elif user.game.type == 3:
            game_type = "watching"

        # Join/creation dates
        since_joined = (ctx.message.created_at - user.joined_at).days
        since_created = (ctx.message.created_at - user.created_at).days
        user_joined = user.joined_at.strftime("%d %b %Y %H:%M:%S")
        user_created = user.created_at.strftime("%d %b %Y %H:%M:%S")

        member_number = sorted(ctx.guild.members,
                               key=lambda m: m.joined_at).index(user) + 1

        # Build the embed
        embed = discord.Embed(color=user.colour)
        embed.set_author(name="Profile for {}".format(user.display_name), icon_url=user.avatar_url)

        _status = "**{status}**, {game_type} **{game}**" if user.game else "**{status}**"
        status = _status.format(status=status, game=game, game_type=game_type)
        embed.add_field(name="Status", value=status, inline=False)

        embed.add_field(name="Roles", inline=False, value="**❯** Bot:\n"
                                                          "{bot_roles}\n\n"
                                                          "**❯** Server:\n"
                                                          "    {server_roles}"
                                                          "".format(server_roles=roles,
                                                                    bot_roles=await self.get_role(user, 4)))
        embed.add_field(name="Joined", inline=False, value="**❯** Server:\n"
                                                           "    **{server_date}** ({server_days} days ago)\n\n"
                                                           "**❯** Discord:\n"
                                                           "    **{discord_date}** ({discord_days} days ago)"
                                                           "".format(server_date=user_joined,
                                                                     server_days=since_joined,
                                                                     discord_date=user_created,
                                                                     discord_days=since_created))

        # User profile data
        if user_info["country"]:
            embed.add_field(name="Country", value=user_info["country"])
        if user_info["age"] is not None:
            embed.add_field(name="Age", value=str(user_info["age"]))
        if user_info["gender"]:
            embed.add_field(name="Gender", value=user_info["gender"])

        if user_info["about"]:
            embed.add_field(name="About Me", value=user_info["about"], inline=False)

        embed.set_footer(text="Member #{} | User ID: {}".format(member_number, user.id))
        await ctx.send(embed=embed)

    @commands.group(name="profile", aliases=["userset"])
    async def userset(self, ctx: commands.Context):
        """
        Change your user profile settings
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @userset.command(name="about")
    async def _user_about(self, ctx: commands.Context, *, about: str=None):
        """
        Sets your About Me message, maximum of 400 characters

        Any text beyond 400 characters is trimmed off
        """
        about = escape(about, mass_mentions=True)[:400]
        await self.config.user(ctx.author).about.set(about)
        if about is None:
            await ctx.send("✅ Cleared your about me", delete_after=15)
        else:
            await ctx.send("✅ Set your about me to:\n```\n{}\n```".format(about), delete_after=15)

    @userset.command(name="age")
    async def _user_age(self, ctx: commands.Context, age: int=None):
        """
        Sets your age
        """
        if age:
            if await self.bot.is_owner(ctx.author):  # Allow the bot owner to bypass this
                pass
            elif age > 99:
                return await ctx.send("\N{THINKING FACE} I'm finding it hard to believe you're actually that old.")
            elif age < 1:
                return await ctx.send("\N{THINKING FACE} Something seems off here.")
        await self.config.user(ctx.author).age.set(age)
        if age is None:
            await ctx.send("✅ Cleared your age", delete_after=15)
        else:
            await ctx.send("✅ Set your age to:\n```\n{}\n```".format(age), delete_after=15)

    @userset.command(name="country")
    async def _user_country(self, ctx: commands.Context, *, country: str = None):
        """
        Set the country you reside in

        Any text beyond 75 characters is trimmed off
        """
        country = escape(country, mass_mentions=True)[:75]
        await self.config.user(ctx.author).country.set(country)
        if country is None:
            await ctx.send("✅ Cleared your country", delete_after=15)
        else:
            await ctx.send("✅ Set your country to:\n```\n{}\n```".format(country), delete_after=15)

    @userset.command(name="gender")
    async def _user_gender(self, ctx: commands.Context, *, gender: str=None):
        """
        Sets your gender

        Any text beyond 50 characters is trimmed off
        """
        gender = escape(gender, mass_mentions=True)[:50]
        await self.config.user(ctx.author).gender.set(gender)
        if gender is None:
            await ctx.send("✅ Cleared your gender", delete_after=15)
        else:
            await ctx.send("✅ Set your gender to:\n```\n{}\n```".format(gender), delete_after=15)

    @userset.command(name="reset")
    async def _user_reset(self, ctx: commands.Context, *, user: discord.User=None):
        """
        Resets your user profile.

        If a user is passed in the command and the command issuer is a bot owner,
        this resets the specified user's profile instead
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
                                                     # All I know is that it supposedly works, and it's pep8 compliant
                                                     check=lambda r, u: u.id == ctx.author.id and (
                                                        not (not (str(r.emoji) == "🇽") and not (str(r.emoji) == "✅")))
                                                     and r.message.id == check_msg.id,
                                                     timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("❌ Operation cancelled.", delete_after=15)
            return await check_msg.delete()
        if str(reaction.emoji) == "🇽":
            await ctx.send("❌ Operation cancelled.", delete_after=15)
            return await check_msg.delete()
        await self.config.user(user).set(self.defaults_user)
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
