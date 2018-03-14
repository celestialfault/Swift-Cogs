from typing import Tuple

import discord
from discord.ext import commands
from discord.ext.commands import CheckFailure
from discord.ext.commands.converter import RoleConverter

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import warning, escape

from odinair_libs.formatting import tick


class RoleTuple(commands.Converter):
    async def convert(self, ctx: RedContext, argument: str):
        second_arg = True
        if argument.startswith('~'):
            argument = argument[1:]
            second_arg = False
        elif argument.startswith('\\'):
            argument = argument[1:]
        return await RoleConverter().convert(ctx, argument), second_arg


class RequireRole:
    """Allow and disallow users to use a bot's commands based on per-guild configurable roles"""
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=90834678413, force_registration=True)
        try:
            self.config.register_guild(**{
                "roles": {
                    "whitelist": [],
                    "blacklist": []
                }
            })
        except KeyError:  # duct tape to resolve Group / Value conflict
            self.config.register_guild(**{"roles": []})

    async def check(self, member: discord.Member = None) -> bool:
        """Check if a member or context is allowed to continue

        Parameters
        -----------
        member: discord.Member
            The member to check

        Returns
        --------
        bool
            A boolean value of if the member given is allowed to use the bot in the members guild or not
        """
        if getattr(member, "guild", None) is None:
            # Always assume a positive result in non-guild contexts
            return True

        guild = member.guild
        if any([await self.bot.is_owner(member), guild.owner.id == member.id,
                member.guild_permissions.administrator]):
            # If the user is the bot owner, the guild owner or a member with the Administrator permission,
            # skip all role checks and assume they're allowed to use the bot
            return True

        guild_opts = await self.config.guild(guild).all()
        guild_roles = guild_opts.get("roles", {})
        if isinstance(guild_roles, list):
            guild_mode = guild_opts.get("mode", "whitelist")
            guild_roles = {guild_mode: guild_roles,
                           # backwards compatibility sucks
                           "blacklist" if guild_mode == "whitelist" else "whitelist": []}

        whitelist = guild_roles.get('whitelist', [])
        blacklist = guild_roles.get('blacklist', [])

        if not any([whitelist, blacklist]):
            return True

        member_roles = [x.id for x in member.roles]
        if blacklist and any([x for x in member_roles if x in blacklist]):
            return False
        if whitelist and not any([x for x in member_roles if x in whitelist]):
            return False

        return True

    async def __global_check_once(self, ctx: RedContext):
        if not await self.check(member=ctx.author):
            raise CheckFailure
        return True

    @commands.command()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def requirerole(self, ctx: RedContext, *roles: RoleTuple):
        """Require specific roles to use the bot in the current guild

        To require a member to __not__ have one or more roles, you can use
        `~` before the role name to treat it as a blacklisted role.

        If a role has a `~` character at the beginning of its name,
        the character can be escaped by prepending a backslash (`\`)
        to the role name. The same also applies if a role has a backslash
        at the beginning of its name.

        Blacklisted roles will override any whitelisted roles
        a member may have, and as such can be a powerful moderation tool.

        More than one whitelisted role given makes this act as an OR check,
        not an AND check. This means a member only needs one of the
        whitelisted roles to use the bot. The same applies to blacklisted roles,
        as a member needs to not have any roles specified as blacklisted
        to use the bot.

        Role names are case sensitive. If a role has spaces in it's name, wrap it in quotes.
        Passing no roles removes the currently set role requirement.

        The guild owner and members with the Administrator permission
        always bypass these requirements, regardless of roles.
        """
        roles: Tuple[Tuple[discord.Role, bool]] = roles  # yes, this is fine
        modes: Tuple[bool] = tuple(x[1] for x in roles)
        roles: Tuple[discord.Role] = tuple(x[0] for x in roles)

        whitelist: Tuple[discord.Role] = tuple(x for x in roles if modes[roles.index(x)])
        blacklist: Tuple[discord.Role] = tuple(x for x in roles if not modes[roles.index(x)])

        if ctx.guild.default_role in roles:
            await ctx.send(warning("I can't set a role requirement with the default role - if you'd like to clear "
                                   "your current role requirements, you can execute this command "
                                   "with no arguments."))
            return

        await self.config.guild(ctx.guild).roles.set({
            "whitelist": [x.id for x in whitelist],
            "blacklist": [x.id for x in blacklist]
        })
        if not roles:
            await ctx.send(tick("Cleared currently set role requirements"))
            return

        whitelist = ", ".join(escape(str(x), mass_mentions=True, formatting=True) for x in whitelist)
        blacklist = ", ".join(escape(str(x), mass_mentions=True, formatting=True) for x in blacklist)

        msg = "A member will now need to pass the following checks to use my commands:\n\n"
        if whitelist:
            msg += f"**Any of the following roles:**\n{whitelist}"
        if whitelist and blacklist:
            msg += "\n\n"
        if blacklist:
            msg += f"**None of the following roles:**\n{blacklist}"

        await ctx.send(tick(msg))
