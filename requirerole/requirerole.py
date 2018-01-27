import discord
from discord.ext.commands.errors import CheckFailure
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import warning, info, escape, bold


class RoleRequiredError(CheckFailure):
    """Raised when a member does not have any of the roles
    a guild requires to use the bot"""
    pass


class RequireRole:
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=90834678413, force_registration=True)
        self.config.register_guild(roles=[], mode="whitelist")
        self.__global_check = self.check

    async def check(self, member: discord.Member or RedContext) -> bool:
        """Check a Member's guild roles, and returns a True or False result depending on the guild's setup"""
        if isinstance(member, RedContext):
            member = member.author

        if not hasattr(member, "guild"):
            # Always assume a positive result in non-guild contexts
            return True

        guild = member.guild

        # We don't care what channel we select here, since the Administrator permission
        # applies across the entire guild
        check_channel = guild.channels[0]
        global_perms = [await self.bot.is_owner(member), guild.owner.id == member.id,
                        check_channel.permissions_for(member).administrator]
        if any(global_perms):
            # If the user is the bot owner, the guild owner or a member with the Administrator permission,
            # skip all role checks and assume they're allowed to use the bot
            return True

        guild_opts = await self.config.guild(guild)()
        guild_roles = guild_opts.get("roles", [])
        if not guild_roles:
            # If there's no roles setup, skip checking and return a positive result
            return True

        mode = guild_opts.get("mode", "whitelist")
        member_roles = [x.id for x in member.roles if x.id in guild_roles]

        if mode == "whitelist":
            return any(member_roles)
        elif mode == "blacklist":
            return not any(member_roles)
        else:  # Assume a positive result if the mode isn't recognized
            return True

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def requirerole(self, ctx: RedContext, *roles: discord.Role):
        """
        Require specific roles to use the bot in the current guild

        If more than one role name is passed, this acts as an any check
        This means that a member only needs one of the given roles to pass the command permission check

        Role names are case sensitive. If a role has spaces in it's name, wrap it in quotes
        Passing no roles removes the currently set role requirement

        The guild owner and members with the Administrator permission always bypass this requirement
        """
        if ctx.guild.default_role in roles:
            await ctx.send(warning("I can't set a role requirement with the default role - maybe try passing no roles"
                                   " to clear the currently set restriction?\n\n"
                                   "You can also set this to blacklist roles with `{prefix}requirerole mode blacklist`"
                                   "".format(prefix=ctx.prefix)))
            return
        await self.config.guild(ctx.guild).roles.set([x.id for x in roles])
        if not roles:
            await ctx.send(info("Cleared currently set role requirements"))
            return
        role_names = [escape(x.name, formatting=True, mass_mentions=True) for x in roles]

        mode_verb = "will now require"
        plural_verb = "one of" if len(roles) != 1 else ""
        if await self.config.guild(ctx.guild).mode() == "blacklist":
            mode_verb = "is now required to not have"
            plural_verb = "any of" if len(roles) != 1 else ""

        info_txt = "A member {mode_verb}{plural_verb} the following role{plural} to use {bot} in this guild:".format(
            mode_verb=mode_verb,
            plural_verb=plural_verb,
            plural="s" if len(roles) != 1 else "",
            bot=bold(str(ctx.guild.me)))

        info_txt = info(info_txt)
        await ctx.send("{}\n\n{}".format(info_txt, ", ".join(role_names)))

    @requirerole.group(name="mode")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def requirerole_mode(self, ctx: RedContext):
        """Change the required role mode"""
        if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == "mode":
            await ctx.send_help()

    @requirerole_mode.command(name="whitelist")
    async def mode_whitelist(self, ctx: RedContext):
        """Set the required role mode to whitelist

        This means that a user requires any of the roles specify to use the bot"""
        await self.config.guild(ctx.guild).mode.set("whitelist")
        await ctx.tick()

    @requirerole_mode.command(name="blacklist")
    async def mode_blacklist(self, ctx: RedContext):
        """Set the required role mode to blacklist

        This means that a user must not have any of the set roles to use the bot"""
        await self.config.guild(ctx.guild).mode.set("blacklist")
        await ctx.tick()
