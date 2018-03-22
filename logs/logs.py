from aiohttp import ClientSession
from typing import Dict, List

import discord
from discord.ext import commands

from redbot.core import checks, Config
from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import warning, info, error

from logs.core import Module, _
from logs.core.module import get_module_cache
from logs.modules import all_modules

from odinair_libs.formatting import tick, cmd_help, flatten
from odinair_libs.menus import confirm


# noinspection PyShadowingNames,PyMethodMayBeStatic
class Logs:
    """Log anything and everything that happens in your server"""

    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = "0.1.0"

    defaults_guild = {
        all_modules[x].name: {
            "_log_channel": None,
            "_webhook": None,
            **all_modules[x].defaults
        } for x in all_modules
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=2401248235421, force_registration=False)
        self.config.register_guild(**self.defaults_guild)
        Module.config = self.config
        Module.bot = self.bot
        Module.session = ClientSession()

    def __unload(self):
        self.bot.loop.create_task(Module.session.close())

    @commands.group(name="logset")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def logset(self, ctx: RedContext):
        """Manage log settings"""
        await cmd_help(ctx, "")

    @logset.command(name="webhook")
    @commands.bot_has_permissions(manage_webhooks=True)
    async def logset_webhook(self, ctx: RedContext, module: str, channel: discord.TextChannel = None):
        """Setup a module to log via a webhook

        This cannot be combined with a conventional log channel set with `[p]logset channel`

        Previously created webhooks that are then unregistered are not cleaned up
        by this command, and have to be removed manually.
        """
        module = await Module.get_module(module, guild=ctx.guild)
        if module is None:
            await ctx.send(warning(_("That module could not be found")))
            return

        await module.module_config.set_raw("_log_channel", value=None)
        if channel is None:
            await module.module_config.set_raw("_webhook", value=None)
            await ctx.send(tick(_("Any previously set webhook has been cleared.")))
            return

        try:
            webhooks: List[discord.Webhook] = await channel.webhooks()
        except discord.Forbidden:
            await ctx.send(error(_("I'm not authorized to manage webhooks in that channel")))
            return

        webhook = None
        for hook in webhooks:
            if hook.name == ctx.me.name:
                webhook = hook
                break

        # Create the webhook if no matching webhooks were found
        if webhook is None:
            # thanks again pycharm, i don't know what i'd do without your warnings about
            # async functions not being async
            # noinspection PyUnresolvedReferences
            webhook = await channel.create_webhook(name=ctx.me.name)

        await module.module_config.set_raw("_webhook", value=webhook.url)
        await module.reload_settings()
        await ctx.send(tick(_("Module **{}** will now log to {} via webhook.").format(module.friendly_name,
                                                                                      channel.mention)))

    @logset.command(name="channel")
    async def logset_channel(self, ctx: RedContext, module: str, channel: discord.TextChannel = None):
        """Set the log channel for a module

        Passing no log channel effectively acts as disabling the module
        """
        module = await Module.get_module(module, guild=ctx.guild)
        if module is None:
            await ctx.send(warning(_("That module could not be found")))
            return
        await module.module_config.set_raw("_log_channel", value=getattr(channel, "id", None))
        await module.module_config.set_raw("_webhook", value=None)
        await module.reload_settings()
        if channel:
            await ctx.send(tick(_("Module **{}** will now log to {}").format(module.friendly_name, channel.mention)))
        else:
            await ctx.send(tick(_("The log channel for module **{}** has been cleared").format(module.friendly_name)))

    @logset.command(name="modules")
    async def logset_modules(self, ctx: RedContext):
        """List all available modules"""
        await ctx.send(info(_("Available modules: {}").format(", ".join(list(all_modules)))))

    @logset.command(name="module")
    async def logset_module(self, ctx: RedContext, module: str, *settings: str):
        """Get or set a module's settings"""
        module = await Module.get_module(module, guild=ctx.guild)
        if module is None:
            await ctx.send(warning(_("That module could not be found")))
            return
        if not settings:
            await ctx.send(embed=status_embed(module))
        else:
            await module.toggle_options(*settings)
            await module.reload_settings()
            await ctx.send(content=tick(_("Updated settings for module {}").format(module.friendly_name)),
                           embed=status_embed(module))

    @logset.command(name="reset")
    async def logset_reset(self, ctx: RedContext):
        """Reset the guild's log settings"""
        if await confirm(ctx, _("Are you sure you want to reset this guild's log settings?"),
                         colour=discord.Colour.red()):
            await self.config.guild(ctx.guild).set(self.defaults_guild)
            await ctx.send(embed=discord.Embed(
                description=_("Guild log settings have been reset."),
                colour=discord.Colour.green()))

            for module in get_module_cache(ctx.guild):
                await module.reload_settings()
        else:
            await ctx.send(embed=discord.Embed(description=_("Okay then."), colour=discord.Colour.gold()))

    ###################
    #    Listeners    #
    ###################

    async def on_message_delete(self, message: discord.Message):
        if not getattr(message, "guild", None):
            return
        module = await Module.get_module("message", message.guild)
        await module.log("delete", message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not getattr(after, "guild", None):
            return
        module = await Module.get_module("message", after.guild)
        await module.log("edit", before, after)

    async def on_member_join(self, member: discord.Member):
        module = await Module.get_module("member", member.guild)
        await module.log("join", member)

    async def on_member_leave(self, member: discord.Member):
        module = await Module.get_module("member", member.guild)
        await module.log("leave", member)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        module = await Module.get_module("member", after.guild)
        await module.log("update", before, after)

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        module = await Module.get_module("channel", channel.guild)
        await module.log("create", channel)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        module = await Module.get_module("channel", channel.guild)
        await module.log("delete", channel)

    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        module = await Module.get_module("channel", after.guild)
        await module.log("update", before, after)

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        if not hasattr(member, "guild"):
            return
        module = await Module.get_module("voice", member.guild)
        await module.log("update", before, after, member)

    async def on_guild_role_create(self, role: discord.Role):
        module = await Module.get_module("role", role.guild)
        await module.log("create", role)

    async def on_guild_role_delete(self, role: discord.Role):
        module = await Module.get_module("role", role.guild)
        await module.log("delete", role)

    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        module = await Module.get_module("role", after.guild)
        await module.log("update", before, after)

    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        module = await Module.get_module("guild", after)
        await module.log("update", before, after)


def add_descriptions(items: List[str], descriptions: Dict[str, str] = None) -> str:
    if descriptions is None:
        descriptions = {}
    for item in items:
        index = items.index(item)
        items[index] = f"**{item}** \N{EM DASH} {descriptions.get(item, _('No description set'))}"
    return "\n".join(items)


def status_embed(module: Module) -> discord.Embed:
    module_opts = flatten(module.settings, sep=":")
    copied = module_opts.copy()
    for opt in copied:
        if opt not in module.opt_keys:
            module_opts.pop(opt)

    enabled = add_descriptions([x for x in module_opts if module_opts[x]], module.option_descriptions)
    disabled = add_descriptions([x for x in module_opts if not module_opts[x]], module.option_descriptions)

    dest = _("Disabled")
    if isinstance(module.log_to, discord.Webhook):
        dest = _("Via webhook")
    elif isinstance(module.log_to, discord.TextChannel):
        dest = _("To channel {}").format(module.log_to.mention)

    embed = discord.Embed(colour=discord.Colour.blurple(), description=module.module_description)
    embed.add_field(name=_("Logging"), value=dest, inline=False)
    embed.set_author(name=_("{} module settings").format(module.friendly_name), icon_url=module.icon_uri())
    embed.add_field(name=_("Enabled"),
                    value=enabled or _("**None** \N{EM DASH} All of this module's options are disabled"),
                    inline=False)
    embed.add_field(name=_("Disabled"),
                    value=disabled or _("**None** \N{EM DASH} All of this module's options are enabled"),
                    inline=False)
    return embed
