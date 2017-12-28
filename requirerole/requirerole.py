import discord
from discord.ext.commands.errors import CheckFailure
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import warning, info, escape


class RoleRequiredError(CheckFailure):
    """Raised when a member does not have any of the roles
    a guild requires to use the bot"""
    pass


class RequireRole:
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=90834678413, force_registration=True)
        self.config.register_guild(roles=[])

    async def __global_check(self, ctx: RedContext):
        if isinstance(ctx.channel, discord.DMChannel) or not ctx.guild:
            # skip checks in direct messages, or wherever we don't have a guild property
            return True

        if await self.bot.is_owner(ctx.author) \
                or ctx.guild.owner.id == ctx.author.id \
                or ctx.channel.permissions_for(ctx.author).administrator:
            # never ignore the bot owner or guild owner
            return True

        required_roles = await self.config.guild(ctx.guild).roles()
        if not required_roles:  # don't bother checking if the guild has no roles setup
            return True

        author_roles = [x.id for x in ctx.author.roles]
        if len([x for x in required_roles if x in author_roles]) == 0:
            raise RoleRequiredError()
        return True

    @commands.command()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def requirerole(self, ctx: RedContext, *roles: discord.Role):
        """
        Require specific roles to use the bot in the current guild

        If more than one role name is passed, this acts as an any check
        This means that a member only needs one of the specified roles to use the bot

        Role names are case sensitive. If a role has spaces in it's name, wrap it in quotes
        Passing no roles removes the currently set role requirement

        The guild owner and members with the Administrator permission always bypass this requirement
        """
        if ctx.guild.default_role in roles:
            await ctx.send("{}\n\n{}".format(warning("Cannot set the role required to the default role"),
                                             info("Tip: Don't pass a role name to clear the role requirement")))
            return
        await self.config.guild(ctx.guild).roles.set([x.id for x in roles])
        if not roles:
            await ctx.send(info("Cleared currently set role requirements"))
        else:
            role_names = [escape(x.name, formatting=True, mass_mentions=True) for x in roles]
            info_txt = info("Set the role{} required to use {} in this guild to:") \
                .format("s" if len(role_names) > 1 else "", ctx.guild.me.name)
            await ctx.send("{}\n\n{}{}".format(
                info_txt, ", ".join(role_names),
                "\n\n**NOTE**: A member will only need one of the set roles to use the bot" if len(role_names) > 1
                else ""))
