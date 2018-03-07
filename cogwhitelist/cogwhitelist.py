import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import warning, pagify, escape

from odinair_libs.formatting import tick


class CogWhitelist:
    """Restrict cogs to approved servers"""
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=7856391, force_registration=True)

        self.config.register_global(
            cogs={}  # dict of lowercase cog names with lists of whitelisted guild IDs
        )

    async def __global_check(self, ctx: RedContext):
        if not ctx.cog or await self.bot.is_owner(ctx.author):
            return True
        cog_name = str(ctx.cog.__class__.__name__).lower()
        cogs = await self.config.cogs()
        if cog_name in cogs:
            guild_id = getattr(getattr(ctx, "guild", None), "id", None)
            return guild_id in cogs[cog_name]
        return True

    def find_cog(self, name: str):
        """Returns a case-sensitive name from a case-insensitive cog name"""
        return discord.utils.find(lambda x: x.lower() == name.lower(), self.bot.cogs.keys())

    @commands.group(name="cogwhitelist")
    @checks.is_owner()
    async def cogwhitelist(self, ctx: RedContext):
        """Manage the cog whitelist"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @cogwhitelist.command(name="add")
    async def cog_add(self, ctx: RedContext, cog: str, guild_id: int=None):
        """Add a cog and/or guild to the list of whitelisted cogs/guilds

        If a guild ID is specified, the guild is added to the cog's list of allowed guilds
        """
        cog = cog.lower()
        proper_name = self.find_cog(cog)
        if proper_name is None:
            await ctx.send(warning(f"That cog either doesn't exist or it isn't currently loaded "
                                   f"(use `{ctx.prefix}cogs` for a list of cogs)"))
            return
        async with self.config.cogs() as cogs:
            if cog not in cogs:
                cogs[cog] = []
                if not guild_id:
                    await ctx.send(tick(f"**{proper_name}** now requires a whitelist to use"))
            elif not guild_id:
                await ctx.send(warning(f"**{proper_name}** already requires a whitelist to use"))
                return
            if guild_id:
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    await ctx.send(warning("I couldn't find a guild with that ID"))
                if guild.id in cogs[cog]:
                    await ctx.send(warning(f"That guild is already allowed to use **{proper_name}**"))
                    return
                cogs[cog].append(guild.id)
                await ctx.send(tick(f"**{escape(guild.name, mass_mentions=True, formatting=True)}** "
                                    f"is now allowed to use **{proper_name}**"))

    @cogwhitelist.command(name="remove")
    async def cog_remove(self, ctx: RedContext, cog: str, guild_id: int=None):
        """Removes a cog or guild from the list of whitelisted cogs/guilds

        If a guild ID is specified, it's removed from the specified cogs' list of allowed guilds
        """
        cog = cog.lower()
        proper_name = self.find_cog(cog) or cog
        async with self.config.cogs() as cogs:
            if cog not in cogs:
                await ctx.send(warning(f"**{proper_name}** doesn't require a whitelist to use"))
                return
            if guild_id:
                if guild_id not in cogs[cog]:
                    await ctx.send(warning(f"That guild isn't allowed to use **{proper_name}**"))
                    return
                cogs[cog].remove(guild_id)
                await ctx.send(warning(f"That guild is no longer allowed to use **{proper_name}**."))
            else:
                cogs.pop(cog)
                await ctx.send(warning(f"**{proper_name}** no longer requires a whitelist to use."))

    @cogwhitelist.command(name="list")
    async def cog_list(self, ctx: RedContext, cog: str=None):
        """List all cogs that require a whitelist, or all the guilds that are allowed to use a cog"""
        cogs = await self.config.cogs()
        if not len(cogs):
            await ctx.send(warning("I have no cogs that require a whitelist to use"))
            return
        if not cog:
            __cogs = []
            for _cog in cogs:
                c = self.find_cog(_cog) or _cog
                __cogs.append(f"[{c}] {len(cogs[_cog])} guilds")
            msg = "{cogs}".format(cogs="\n".join(__cogs))
            await ctx.send_interactive(pagify(msg), box_lang="ini")
        else:
            guilds = [self.bot.get_guild(x) for x in cogs[cog.lower()]]
            guilds = [x for x in guilds if x]
            if not len(guilds):
                await ctx.send(warning("No guilds that I'm currently in are allowed to use that cog"))
                return
            c = self.find_cog(cog) or cog
            guilds = "\n".join(f"{x.name!r}  # ID: {x.id}" for x in guilds)
            msg = f"# Guilds that are allowed to use {c!r}:\n\n{guilds}"
            await ctx.send_interactive(pagify(msg), box_lang="py")
