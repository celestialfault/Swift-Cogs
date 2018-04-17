import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.i18n import CogI18n
from redbot.core.utils.chat_formatting import warning, escape, info, inline

from cog_shared.odinair_libs import tick, fmt, cog_name, ConfirmMenu, PaginateMenu, chunks

_ = CogI18n("CogWhitelist", __file__)


class CogWhitelist:
    """Restrict cog usage to approved servers"""

    __author__ = "odinair <odinair@odinair.xyz>"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=7856391, force_registration=True)

        self.config.register_global(
            cogs={}  # dict of lowercase cog names with lists of whitelisted guild IDs
        )

    async def is_whitelisted(self, cog: str, guild: discord.Guild = None):
        guilds = await self.config.cogs.get_raw(cog.lower(), default=None)
        return guilds is None or getattr(guild, "id", None) in guilds

    async def __global_check(self, ctx: RedContext):
        if not ctx.cog or await self.bot.is_owner(ctx.author):
            return True
        return await self.is_whitelisted(ctx.cog.__class__.__name__, ctx.guild)

    @commands.group(name="cogwhitelist")
    @checks.is_owner()
    async def cogwhitelist(self, ctx: RedContext):
        """Manage the cog whitelist"""
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @cogwhitelist.command(name="add")
    async def cogwhitelist_add(self, ctx: RedContext, cog: str, guild_id: int = None):
        """Add a cog and/or guild to the list of whitelisted cogs/guilds

        If a guild ID is specified, the guild is added to the cog's list of allowed guilds

        Cogs are handled on a case-insensitive name basis, and as such if you replace
        a cog with another with the same name, it will keep the same settings
        as any cog previously setup with that name, regardless of capitalization.
        """
        proper_name = cog_name(self.bot, cog)
        if not cog:
            return await ctx.send(_("No cog with that name is currently loaded"))
        cog = str(proper_name).lower()
        async with self.config.cogs() as cogs:
            if cog not in cogs:
                cogs[cog] = []
                if not guild_id:
                    await fmt(ctx, _("**{cog}** now requires a whitelist to use"), cog=proper_name)
            elif not guild_id:
                return await fmt(ctx, warning(_("**{cog}** already requires a whitelist to use")), cog=proper_name)
            if guild_id:
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    await ctx.send(warning(_("I couldn't find a guild with that ID")))
                if guild.id in cogs[cog]:
                    return await fmt(ctx, warning(_("That guild is already allowed to use **{cog}**")), cog=proper_name)
                cogs[cog].append(guild.id)
                await fmt(ctx, tick(_("**{guild_name}** is now allowed to use **{cog}**")),
                          guild_name=escape(guild.name, mass_mentions=True, formatting=True),
                          cog=proper_name)

    @cogwhitelist.command(name="remove")
    async def cogwhitelist_remove(self, ctx: RedContext, cog: str, guild_id: int = None):
        """Removes a cog or guild from the list of whitelisted cogs/guilds

        If a guild ID is specified, it's removed from the specified cogs' list of allowed guilds
        """
        cog = cog.lower()
        proper_name = cog_name(self.bot, cog) or cog
        async with self.config.cogs() as cogs:
            if cog not in cogs:
                return await fmt(ctx, warning(_("**{cog}** doesn't currently require a whitelist to use")),
                                 cog=proper_name)
            if guild_id:
                if guild_id not in cogs[cog]:
                    return await fmt(ctx, warning(_("That guild isn't allowed to use **{cog}**")), cog=proper_name)
                cogs[cog].remove(guild_id)
                await fmt(ctx, tick(_("That guild is no longer allowed to use **{cog}**.")), cog=proper_name)
            else:
                cogs.pop(cog)
                await fmt(ctx, tick(_("**{cog}** no longer requires a whitelist to use")), cog=proper_name)

    @cogwhitelist.command(name="reset")
    async def cogwhitelist_reset(self, ctx: RedContext):
        """Reset whitelisted cog settings"""
        cogs = len(await self.config.cogs())
        if not cogs:
            return await fmt(ctx, info(_("No cogs are currently setup to require a whitelist to use, and as such "
                                         "you cannot reset any cog whitelist settings.")))

        warn_str = warning(_(
            "Are you sure you want to reset your cog whitelist settings?\n"
            "This action will make {cogs} cog(s) usable by any server.\n\n"
            "Unless you have a time machine, **this action cannot be undone.**"
        ))

        if await ConfirmMenu(ctx=ctx, content=warn_str.format(cogs=cogs)).prompt():
            await self.config.cogs.set({})
            await ctx.tick()
        else:
            await ctx.send(_("Ok then."))

    @cogwhitelist.command(name="list")
    async def cogwhitelist_list(self, ctx: RedContext, cog: str = None):
        """List all cogs that require a whitelist, or all the guilds that are allowed to use a cog"""
        cogs = await self.config.cogs()
        if not cogs:
            await ctx.send(warning("I have no cogs that require a whitelist to use"))
            return

        if cog is None:
            await self._list_cogs(ctx)
        else:
            await self._list_guilds(ctx, cog)

    async def _list_cogs(self, ctx: RedContext):
        cogs = await self.config.cogs()
        if not cogs:
            await ctx.send(warning(_("I have no cogs that require a whitelist to use")))
            return

        def converter(page, page_id, total_pages):
            embed = discord.Embed(colour=ctx.me.colour, title=_("Whitelisted Cogs"))

            for cog, guild_ids in page.items():
                cog = cog_name(self.bot, cog) or cog
                status = _("This guild is currently allowed to use this cog") \
                    if getattr(ctx.guild, "id", None) in guild_ids \
                    else _("This guild is **not** currently allowed to use this cog")

                if cog not in self.bot.cogs:
                    status = _("**This cog is not currently loaded.**")

                value = _(
                    "Current whitelisted guild(s): {guilds}\n"
                    "Use `{prefix}cogwhitelist list {cog}` to the whitelisted guild(s).\n"
                    "\n"
                    "{status}"
                ).format(
                    guilds=len(guild_ids),
                    status=status,
                    prefix=ctx.prefix,
                    cog=cog
                )

                embed.add_field(name=cog, value=value)

            embed.set_footer(text=_("Page {}/{}").format(page_id + 1, total_pages))
            return embed

        async with PaginateMenu(ctx, pages=[dict(x) for x in chunks(list(cogs.items()), 6)],
                                converter=converter, actions={}):
            pass

    async def _list_guilds(self, ctx: RedContext, cog: str):
        cogs = await self.config.cogs()
        if cog.lower() not in cogs:
            await ctx.send(warning(_("That cog doesn't require a whitelist to use")))
            return

        proper_name = cog_name(self.bot, cog) or cog

        def converter(page, page_id, total_pages):
            embed = discord.Embed(colour=ctx.me.colour, title=_("Whitelisted Guilds"),
                                  description=_("The following guilds are allowed to use {}").format(proper_name))

            for guild_id in page:
                guild = self.bot.get_guild(guild_id)
                try:
                    name = escape(guild.name, formatting=True)
                except AttributeError:
                    name = inline(_("Unknown guild"))

                embed.add_field(name=_("Guild #{}").format(((page_id * 10) + page.index(guild_id)) + 1),
                                value=_("**Name:** {name}\n**ID:** `{id}`").format(name=name, id=guild_id),
                                inline=False)

            embed.set_footer(text=_("Page {}/{}").format(page_id + 1, total_pages))
            return embed

        async with PaginateMenu(ctx, pages=chunks(cogs[cog.lower()], 6),
                                converter=converter, actions={}):
            pass
