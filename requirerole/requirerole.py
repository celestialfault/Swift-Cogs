import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import error, warning, info, escape


class RequireRole:
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9083469835, force_registration=True)
        self.config.register_guild(roles=[])

    async def __global_check(self, ctx: commands.Context):
        if isinstance(ctx.channel, discord.DMChannel) or not ctx.guild:
            # skip checks in direct messages, or wherever we don't have a guild property
            return True
        if await self.bot.is_owner(ctx.author)\
                or ctx.guild.owner.id == ctx.author.id\
                or ctx.channel.permissions_for(ctx.author).administrator:
            # never ignore the bot owner or guild owner
            return True
        require_roles = await self.config.guild(ctx.guild).roles()
        if not require_roles:
            return True
        # list of roles the guild has
        guild_roles = [x.name.lower() for x in ctx.author.roles]
        for guild_role in require_roles:
            # lowercase the role name
            guild_role = guild_role.lower()
            # check if the role name is in the user's roles
            if guild_role in guild_roles:
                return True
        return False

    @commands.command(name="requirerole", aliases=["requireroles"])
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def _requirerole(self, ctx: RedContext, *role_names: str):
        """
        Require specific roles to use the bot in the current guild

        If a role name has spaces in it's name, wrap it in quotes

        Passing no role name clears the currently set role requirement

        The guild owner and members with the Administrator permission always bypass this requirement
        """
        if "@everyone" in [x.lower() for x in role_names]:
            await ctx.send("{}\n\n{}".format(warning("Cannot set the role required to the everyone role"),
                                             info("Tip: Don't pass a role name to clear the role requirement")))
            return
        guild_roles = [x.name.lower() for x in ctx.guild.roles]
        for role in role_names:
            if role.lower() not in guild_roles:
                role = escape(role, formatting=True, mass_mentions=True)
                await ctx.send(error("There is no role named **{}** in this guild".format(role)))
                return
        await self.config.guild(ctx.guild).roles.set(role_names)
        if not role_names:
            await ctx.send(info("Cleared currently set role requirements"))
        else:
            role_names = [escape(x, formatting=True, mass_mentions=True) for x in role_names]
            await ctx.send("{}\n\n{}{}".format(
                info("Set the role{} required to use {} in this guild to:")
                .format("s" if len(role_names) > 1 else "",
                        ctx.guild.me.name),
                ", ".join(role_names),
                "\n\n**NOTE**: The role requirement is an __OR check__"
                "\nThis means that a member only needs one of the set roles to use the bot"
                if len(role_names) > 1 else ""))
