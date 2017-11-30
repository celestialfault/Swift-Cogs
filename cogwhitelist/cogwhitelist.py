import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import error, info, warning


class CogWhitelist:
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=7856390, force_registration=True)

        self.config.register_global(cogs=[])
        self.config.register_guild(cogs=[])

    async def __global_check(self, ctx: commands.Context):
        if not ctx.cog or not ctx.cog.__class__ or await self.bot.is_owner(ctx.author):
            return True
        cog_name = ctx.cog.__class__.__name__
        if cog_name in await self.config.cogs():
            return cog_name in await self.config.guild(ctx.guild).cogs()
        return True

    @commands.group(name="cogwhitelist")
    @checks.is_owner()
    async def _cogwhitelist(self, ctx: RedContext):
        """
        Manage the cog whitelist
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @_cogwhitelist.group(name="cogs", aliases=["cog"])
    async def cog_whitelist(self, ctx: RedContext):
        """
        Manage which cogs require a whitelist to use
        """
        if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == "cogs":
            await ctx.send_help()

    @cog_whitelist.command(name="clear")
    async def whitelist_cog_clear(self, ctx: RedContext):
        """
        Clears the cog whitelist
        """
        await self.config.cogs.set([])
        await ctx.send(info("Cleared cog whitelist"))

    @cog_whitelist.command(name="add")
    async def whitelist_cog(self, ctx: RedContext, cog_name: str):
        """
        Adds a cog to the whitelist
        """
        whitelist = list(await self.config.cogs())
        cog_name = discord.utils.find(lambda cog: str(cog).lower() == cog_name.lower(), self.bot.cogs)
        if not cog_name:
            await ctx.send(error("That cog wasn't found"))
            return
        if cog_name in whitelist:
            await ctx.send(warning("That cog is already on the cog whitelist"))
            return
        cogs = list(await self.config.cogs())
        cogs.append(cog_name)
        await self.config.cogs.set(cogs)
        await ctx.send(info("Successfully whitelisted cog **%s**" % cog_name))

    @cog_whitelist.command(name="remove")
    async def unwhitelist_cog(self, ctx: RedContext, cog_name: str):
        """
        Removes a cog from the whitelist
        """
        cog_name = discord.utils.find(lambda cog: str(cog).lower() == cog_name.lower(), self.bot.cogs)
        if not cog_name:
            await ctx.send(error("That cog wasn't found"))
            return
        cogs = list(await self.config.cogs())
        if cog_name not in cogs:
            await ctx.send(warning("That cog doesn't require a whitelist to use currently"))
            return
        del cogs[cogs.index(cog_name)]
        await self.config.cogs.set(cogs)
        await ctx.send(info("Successfully unwhitelisted cog **%s**" % cog_name))

    @cog_whitelist.command(name="list")
    async def list_cogs(self, ctx: RedContext):
        """
        Lists all cogs and their whitelist status
        """
        whitelisted_cogs = await self.config.cogs()
        whitelisted_cogs = "\n".join(list(whitelisted_cogs))
        if not whitelisted_cogs:
            whitelisted_cogs = error("No cogs currently require a whitelist to use")
        whitelisted_cogs = info("Cogs that require a whitelist to use:\n\n") + whitelisted_cogs
        await ctx.send(whitelisted_cogs)

    @_cogwhitelist.group(name="guilds", aliases=["guild"])
    async def guild_whitelist(self, ctx: RedContext):
        """
        Manage which cogs require a whitelist to use
        """
        if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == "guilds":
            await ctx.send_help()

    @guild_whitelist.command(name="add")
    async def guild_whitelist_add(self, ctx: RedContext, cog_name: str, guild_id: int=None):
        """
        Allows the current or specified guild to use the specified cog
        """
        guild = ctx.guild if not guild_id else self.bot.get_guild(guild_id)
        if not guild:
            await ctx.send(error("That guild could not be found"))
            return
        cog_name = discord.utils.find(lambda cog: str(cog).lower() == cog_name.lower(), self.bot.cogs)
        if not cog_name:
            await ctx.send(error("That cog could not be found"))
            return
        guild_whitelist = list(await self.config.guild(guild).cogs())
        if cog_name.lower() not in [x.lower() for x in await self.config.cogs()]:
            await ctx.send(error("That cog doesn't require per-guild whitelisting to use"))
            return
        if cog_name.lower() in [x.lower() for x in guild_whitelist]:
            await ctx.send(warning("That guild is already allowed to use that cog"))
            return
        guild_whitelist.append(cog_name)
        await self.config.guild(guild).cogs.set(guild_whitelist)
        await ctx.send(info("**{}** is now allowed to use commands from **{}**").format(guild.name, cog_name))

    @guild_whitelist.command(name="remove")
    async def guild_whitelist_remove(self, ctx: RedContext, cog_name: str, guild_id: int=None):
        """
        Removes a previous cog whitelist for the current or specified guild
        """
        guild = ctx.guild if not guild_id else self.bot.get_guild(guild_id)
        if not guild:
            await ctx.send(error("That guild could not be found"))
            return
        cog_name = discord.utils.find(lambda cog: str(cog).lower() == cog_name.lower(), self.bot.cogs)
        if not cog_name:
            await ctx.send(error("That cog could not be found"))
            return
        guild_whitelist = list(await self.config.guild(guild).cogs())
        if cog_name.lower() not in [x.lower() for x in guild_whitelist]:
            await ctx.send(warning("That guild isn't allowed to use that cog already"))
            return
        del guild_whitelist[guild_whitelist.index(cog_name)]
        await self.config.guild(guild).cogs.set(guild_whitelist)
        await ctx.send(info("**{}** is no longer allowed to use commands from **{}**").format(guild.name, cog_name))

    @guild_whitelist.command(name="list")
    async def guild_whitelist_list(self, ctx: RedContext, guild_id: int=None):
        """
        Lists all cogs the current guild is allowed to use
        """
        guild = ctx.guild if not guild_id else self.bot.get_guild(guild_id)
        if not guild:
            await ctx.send(error("That guild could not be found"))
            return
        whitelisted_cogs = await self.config.guild(guild).cogs()
        txt = "\n".join(whitelisted_cogs)
        if not txt:
            txt = error("This guild isn't allowed to use any whitelisted cogs")
        txt = info("Whitelisted cogs:\n\n") + txt
        await ctx.send(txt)

    @guild_whitelist.command(name="clear")
    async def guild_whitelist_clear(self, ctx: RedContext, guild_id: int=None):
        """
        Clears whitelist for the current or specified guild
        """
        guild = ctx.guild if not guild_id else self.bot.get_guild(guild_id)
        if not guild:
            await ctx.send(error("That guild could not be found"))
            return
        await self.config.guild(guild).cogs.set([])
        await ctx.send(info("Whitelisted cogs cleared for this guild"))
