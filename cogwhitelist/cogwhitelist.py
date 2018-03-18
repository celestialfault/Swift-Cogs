import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.i18n import CogI18n
from redbot.core.utils.chat_formatting import warning, pagify, escape

from odinair_libs.formatting import tick
from odinair_libs.converters import cog_name
from odinair_libs.menus import confirm

_ = CogI18n("CogWhitelist", __file__)


class Cog(commands.Converter):
    async def convert(self, ctx: RedContext, argument: str):
        bot: Red = ctx.bot
        cog = cog_name(bot, argument)
        if cog:
            return cog
        else:
            raise commands.BadArgument(_("Cog `{}` could not be found").format(argument))


class CogWhitelist:
    """Restrict cogs to approved servers"""

    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = "0.1.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=7856391, force_registration=True)

        self.config.register_global(
            cogs={}  # dict of lowercase cog names with lists of whitelisted guild IDs
        )

    async def __global_check(self, ctx: RedContext):
        if not ctx.cog or await self.bot.is_owner(ctx.author):
            return True
        cog_name_ = str(ctx.cog.__class__.__name__).lower()
        cogs = await self.config.cogs()
        if cog_name_ in cogs:
            guild_id = getattr(getattr(ctx, "guild", None), "id", None)
            return guild_id in cogs[cog_name_]
        return True

    @commands.group(name="cogwhitelist")
    @checks.is_owner()
    async def cogwhitelist(self, ctx: RedContext):
        """Manage the cog whitelist"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @cogwhitelist.command(name="add")
    async def cog_add(self, ctx: RedContext, cog: Cog, guild_id: int=None):
        """Add a cog and/or guild to the list of whitelisted cogs/guilds

        If a guild ID is specified, the guild is added to the cog's list of allowed guilds
        """
        proper_name = str(cog)
        cog = str(cog).lower()
        async with self.config.cogs() as cogs:
            if cog not in cogs:
                cogs[cog] = []
                if not guild_id:
                    await ctx.send(tick(_("**{}** now requires a whitelist to use").format(proper_name)))
            elif not guild_id:
                await ctx.send(warning(_("**{}** already requires a whitelist to use").format(proper_name)))
                return
            if guild_id:
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    await ctx.send(warning(_("I couldn't find a guild with that ID")))
                if guild.id in cogs[cog]:
                    await ctx.send(warning(_("That guild is already allowed to use **{}**").format(proper_name)))
                    return
                cogs[cog].append(guild.id)
                await ctx.send(tick(_("**{}** is now allowed to use **{}**").format(
                    escape(guild.name, mass_mentions=True, formatting=True), proper_name)))

    @cogwhitelist.command(name="remove")
    async def cog_remove(self, ctx: RedContext, cog: str, guild_id: int=None):
        """Removes a cog or guild from the list of whitelisted cogs/guilds

        If a guild ID is specified, it's removed from the specified cogs' list of allowed guilds
        """
        cog = cog.lower()
        proper_name = cog_name(self.bot, cog) or cog
        async with self.config.cogs() as cogs:
            if cog not in cogs:
                await ctx.send(warning(_("**{}** doesn't require a whitelist to use").format(proper_name)))
                return
            if guild_id:
                if guild_id not in cogs[cog]:
                    await ctx.send(warning(_("That guild isn't allowed to use **{}**").format(proper_name)))
                    return
                cogs[cog].remove(guild_id)
                await ctx.send(tick(_("That guild is no longer allowed to use **{}**.").format(proper_name)))
            else:
                cogs.pop(cog)
                await ctx.send(tick(_("**{}** no longer requires a whitelist to use.").format(proper_name)))

    @cogwhitelist.command(name="reset")
    async def cogwhitelist_reset(self, ctx: RedContext):
        if await confirm(ctx=ctx, message=_("Are you sure you want to reset your whitelisted cogs?\n\n"
                                            "**This action is irreversable!**"), colour=discord.Colour.red()):
            await self.config.cogs.set({})
            await ctx.tick()
        else:
            await ctx.send(_("Ok then."))

    @cogwhitelist.command(name="list")
    async def cog_list(self, ctx: RedContext, cog: str=None):
        """List all cogs that require a whitelist, or all the guilds that are allowed to use a cog"""
        cogs = await self.config.cogs()
        if not cogs:
            await ctx.send(warning("I have no cogs that require a whitelist to use"))
            return
        if not cog:
            __cogs = []
            for _cog in cogs:
                proper_name = cog_name(self.bot, _cog) or _cog
                __cogs.append(_("[{}] {} guilds").format(proper_name, len(cogs[_cog])))
            msg = "\n".join(__cogs)
            await ctx.send_interactive(pagify(msg), box_lang="ini")
        else:
            print(cog, cogs)
            cog = cog.lower()
            if cog not in cogs:
                await ctx.send(warning(_("That cog doesn't require a whitelist to use")))
                return
            guilds = [self.bot.get_guild(x) for x in cogs[cog]]
            guilds = [x for x in guilds if x]
            if not len(guilds):
                await ctx.send(warning(_("No guilds that I'm currently in are allowed to use that cog")))
                return
            proper_name = cog_name(self.bot, cog) or cog
            guilds = "\n".join(f"{x.name!r}  # {x.id}" for x in guilds)
            msg = _("# Guilds that are allowed to use {}:\n\n{}").format(repr(proper_name), guilds)
            await ctx.send_interactive(pagify(msg), box_lang="py")
