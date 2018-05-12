from typing import Tuple

import discord
from discord.ext.commands.converter import RoleConverter
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import escape, warning

from cog_shared.swift_libs import tick

_ = Translator("RequireRole", __file__)


class SeenSet(set):  # quick and dirty utility class to filter out duplicated roles

    def mark_seen(self, element):
        if element in self:
            return False
        self.add(element)
        return True


class RoleTuple(commands.Converter):

    async def convert(self, ctx: commands.Context, argument: str):
        whitelist = True
        if argument.startswith("~"):
            argument = argument[1:]
            whitelist = False
        elif argument.startswith("\\"):
            argument = argument[1:]
        return await RoleConverter().convert(ctx, argument), whitelist


@cog_i18n(_)
class RequireRole:
    """Allow and disallow users to use a bot's commands based on per-guild configurable roles"""

    __author__ = "odinair <odinair@odinair.xyz>"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=90834678413, force_registration=True)
        self.config.register_guild(**{"roles": {"whitelist": [], "blacklist": []}})

    async def check(self, member: discord.Member = None) -> bool:
        """Check if a member or context is allowed to continue

        Parameters
        -----------
        member: discord.Member
            The member to check

        Returns
        --------
        bool
            A boolean value indicating if the member given is allowed to use the bot
            in their current guild or not
        """
        if getattr(member, "guild", None) is None:
            # Always assume a positive result in non-guild contexts
            return True

        guild = member.guild
        if any(
            [
                await self.bot.is_owner(member),
                guild.owner.id == member.id,
                member.guild_permissions.administrator,
            ]
        ):
            # If the user is the bot owner, the guild owner, or a member with the Administrator
            # permission, skip all role checks and assume they're allowed to use the bot
            return True

        guild_opts = await self.config.guild(guild).all()
        guild_roles = guild_opts.get("roles", {})
        if isinstance(guild_roles, list):
            guild_mode = guild_opts.get("mode", "whitelist")
            guild_roles = {
                guild_mode: guild_roles,
                # backwards compatibility sucks
                "blacklist" if guild_mode == "whitelist" else "whitelist": [],
            }

        whitelist = guild_roles.get("whitelist", [])
        blacklist = guild_roles.get("blacklist", [])

        if not any([whitelist, blacklist]):
            return True

        member_roles = [x.id for x in member.roles]
        if blacklist and any([x for x in member_roles if x in blacklist]):
            return False
        if whitelist and not any([x for x in member_roles if x in whitelist]):
            return False

        return True

    async def __global_check(self, ctx: commands.Context):
        if not await self.check(member=ctx.author):
            raise commands.CheckFailure()
        return True

    @commands.command()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def requirerole(self, ctx: commands.Context, *roles: RoleTuple):
        """Require one of any specific roles to use the bot in the current guild

        To require a member to __not__ have one or more roles, you can use
        `~` before the role name to treat it as a blacklisted role.
        If a role name has `~` at the start of it's name, you can escape
        it with a backslash (`\`) character. Blacklisted roles override
        any possible whitelisted roles a member may have.

        Role names are case sensitive. If a role has spaces in it's name, wrap it in quotes.
        Passing no roles removes any currently set role requirements.

        The guild owner and members with the Administrator permission
        always bypass these requirements, regardless of roles."""
        seen = SeenSet()
        roles = tuple(
            (k, v) for k, v in roles if seen.mark_seen(k)
        )  # type: Tuple[Tuple[discord.Role, bool]]
        whitelist = tuple(r for r, v in roles if v)  # type: Tuple[discord.Role]
        blacklist = tuple(r for r, v in roles if not v)  # type: Tuple[discord.Role]

        if ctx.guild.default_role in roles:
            await ctx.send(
                warning(
                    _(
                        "I can't set a role requirement with the guild's default role - "
                        "if you'd like to clear your current role requirements, "
                        "you can execute this command with no arguments to do so."
                    )
                )
            )
            return

        await self.config.guild(ctx.guild).roles.set(
            {"whitelist": [x.id for x in whitelist], "blacklist": [x.id for x in blacklist]}
        )
        if not roles:
            await ctx.send(tick(_("Cleared currently set role requirements.")))
            return

        whitelist = ", ".join(
            escape(str(x), mass_mentions=True, formatting=True) for x in whitelist
        )
        blacklist = ", ".join(
            escape(str(x), mass_mentions=True, formatting=True) for x in blacklist
        )

        msg = _("A member will now need to pass the following checks to use my commands:\n\n")
        if whitelist:
            msg += _("**Any of the following roles:**\n{roles}").format(roles=whitelist)
        if whitelist and blacklist:
            msg += "\n\n"
        if blacklist:
            msg += _("**None of the following roles:**\n{roles}").format(roles=blacklist)

        await ctx.send(tick(msg))
