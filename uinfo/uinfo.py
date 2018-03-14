import discord
from discord.ext import commands

from redbot.core import RedContext
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import escape, bold

from odinair_libs.formatting import td_format, normalize


class UInfo:
    def __init__(self, bot: Red):
        self.bot = bot

    @staticmethod
    def plural(*items: str):
        items = list(items)
        if len(items) >= 3:
            last = items.pop()
            joined = ", ".join(items)
            return f"{joined} and {last}"
        else:
            return ", ".join(items)

    async def get_bot_role(self, member: discord.Member):
        if member.bot:
            return None
        msgs = []

        if await self.bot.is_owner(member):
            msgs.append("\N{HAMMER AND WRENCH} **Bot Owner**")

        if member.guild.owner.id == member.id:
            msgs.append("\N{KEY} Guild Owner")
        elif await self.bot.is_admin(member):
            msgs.append("\N{HAMMER} Server Administrator")
        elif await self.bot.is_mod(member):
            msgs.append("\N{SHIELD} Server Moderator")
        else:
            msgs.append("\N{BUSTS IN SILHOUETTE} Server Member")

        return "\n".join(msgs)

    def get_activity(self, member: discord.Member):
        game = bold(getattr(member.activity, "name", None))
        game_type = None

        if member.activity is None:
            pass

        elif member.activity.type == discord.ActivityType.playing:
            game_type = "\N{VIDEO GAME} Playing"

        elif member.activity.type == discord.ActivityType.streaming:
            game_type = "\N{VIDEO CAMERA} Streaming"
            game = bold(f"[{member.activity}]({member.activity.url})")

        elif member.activity.type == discord.ActivityType.listening:
            game_type = "\N{MUSICAL NOTE} Listening to"
            if isinstance(member.activity, discord.Spotify):
                game = f"{self.plural(*[bold(x) for x in member.activity.artists])} \N{EM DASH} " \
                       f"**{member.activity.title}** on **Spotify**"

        elif member.activity.type == discord.ActivityType.watching:
            game_type = "\N{FILM PROJECTOR} Watching"

        return game, game_type

    @commands.command(aliases=["uinfo", "whois"])
    @commands.guild_only()
    async def user(self, ctx: RedContext, *, user: discord.Member = None):
        """Displays your or a specified user's profile"""
        user = user or ctx.author
        member_number = sorted(ctx.guild.members, key=lambda m: m.joined_at).index(user) + 1

        since_created = td_format(user.created_at - ctx.message.created_at, append_str=True)
        since_joined = td_format(user.joined_at - ctx.message.created_at, append_str=True)

        colour = user.colour
        if colour == discord.Colour.default():
            colour = discord.Embed.Empty

        game, game_type = self.get_activity(user)
        status = normalize(str(user.status), dnd="do not disturb")
        description = f"\N{EARTH GLOBE AMERICAS} {status}"

        if game:
            description += f"\n{game_type} {game}"
        if user.nick:
            description += f"\n\N{LABEL} Nicknamed as {bold(escape(user.nick, formatting=True))}"

        embed = discord.Embed(title=str(user), colour=colour, description=description)
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text=f"Member #{member_number} | User ID: {user.id}")

        bot_roles = await self.get_bot_role(user)
        if bot_roles is not None:
            embed.add_field(name="Bot Roles", value=bot_roles, inline=False)

        roles = reversed([escape(x.name, formatting=True) for x in user.roles if x.name != "@everyone"])
        if roles:
            embed.add_field(name="Guild Roles", value=", ".join(roles or ["None"]), inline=False)

        embed.add_field(name="Joined Discord", value=since_created, inline=False)
        embed.add_field(name="Joined Guild", value=since_joined, inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="avatar")
    @commands.guild_only()
    async def avatar(self, ctx: RedContext, *, user: discord.Member = None):
        """Get the avatar of yourself or a specified user"""
        user = ctx.author if user is None else user
        embed = discord.Embed(colour=user.colour, title="{0!s}'s avatar".format(user))
        embed.set_image(url=user.avatar_url_as(static_format="png"))
        await ctx.send(embed=embed)
