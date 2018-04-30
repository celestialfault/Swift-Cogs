import contextlib

from aiohttp import ClientSession
from typing import List, Optional, Type

import discord
from discord.ext import commands
from discord.raw_models import RawBulkMessageDeleteEvent

from redbot.core import checks, Config
from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import warning, info, error, inline, bold

from logs.core import Module, get_module, i18n
from logs.core.module import log
from logs.modules import all_modules

from cog_shared.odinair_libs import tick, cmd_help, fmt, ConfirmMenu, prompt, cmd_group


def ignore_handler(*, parent=commands, converters: List[Type[commands.Converter]],
                   conf_opt: str, remove: bool = False, **kwargs):
    # Yes: This is probably the worst idea that's been implemented yet in this entire cog to date.
    # But I mean, hey; it sure beats the dozen+ commands with functionally the exact same code
    # that was here before.
    name = kwargs.pop('name', 'add' if remove is False else 'remove')

    # noinspection PyUnusedLocal
    async def _command(self, ctx: RedContext, *, item):
        new_item = ...
        for converter in converters:
            with contextlib.suppress(commands.BadArgument):
                new_item = await converter().convert(ctx, item)
                break
        if new_item is ...:
            raise commands.BadArgument
        item = getattr(item, "id", item)
        async with Module.config.guild(ctx.guild).ignore.get_attr(conf_opt)() as ignored:
            if remove is False:
                if item in ignored:
                    await ctx.send(warning(i18n("That item is already currently being ignored")))
                    return
                ignored.append(item)
            else:
                if item not in ignored:
                    await ctx.send(warning(i18n("That item is not currently being ignored")))
                    return
                ignored.remove(item)
            log.debug('{} {!r} to/from {!r} {} ignore list'.format(name, new_item, ctx.guild, conf_opt))
            await ctx.tick()

    if conf_opt == 'guild':
        # noinspection PyUnusedLocal
        async def _command(self, ctx: RedContext, toggle: bool = None):  # noqa
            if toggle is None:
                toggle = not await Module.config.guild(ctx.guild).ignore.guild()
            await Module.config.guild(ctx.guild).ignore.guild.set(toggle)
            await ctx.send(tick(i18n("Now ignoring the current server") if toggle else
                                i18n("No longer ignoring the current server")))

    return parent.command(name=name, **kwargs)(_command)


# noinspection PyMethodMayBeStatic
class Logs:
    """Log anything and everything that happens in your server"""

    __author__ = "odinair <odinair@odinair.xyz>"

    defaults_global = {
        **{
            x.name: {
                "_log_channel": None,
                "_webhook": None,
                **x(guild=None).defaults
            } for x in all_modules.values() if x(guild=None).is_global is True
        },
        "ignore": {
            "channels": [],
            "members": [],
            "roles": [],
            "member_roles": []
        }
    }

    defaults_guild = {
        **{
            x.name: {
                "_log_channel": None,
                "_webhook": None,
                **x(guild=None).defaults
            } for x in all_modules.values() if x(guild=None).is_global is not True
        },
        "ignore": {
            "channels": [],
            "members": [],
            "roles": [],
            "member_roles": [],
            "guild": False
        }
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=2401248235421, force_registration=False)
        self.config.register_guild(**self.defaults_guild)
        self.config.register_global(**self.defaults_global)
        Module.config = self.config
        Module.bot = self.bot
        Module.session = ClientSession()

    def __unload(self):
        Module.session.close()

    @commands.group(name="logset")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def logset(self, ctx: RedContext):
        """Manage log settings"""
        await cmd_help(ctx)

    @logset.command(name="setup")
    async def logset_setup(self, ctx: RedContext):
        """Quick-start for logging settings"""
        for module_name in all_modules.keys():
            module = get_module(module_id=module_name, guild=ctx.guild)
            if not await module.can_modify_settings(ctx.author):
                continue
            async with ConfirmMenu(ctx, message=i18n("Would you like to enable the **{}** module?").format(
                    module.friendly_name)) as result:
                await module.module_config.clear()
                if not result:
                    continue
                channel = None  # type: Optional[discord.TextChannel]
                while channel is None:
                    given = await prompt(ctx, content=i18n("What channel would you like to log to?"), timeout=90,
                                         delete_messages=True)
                    if given is None:
                        break
                    try:
                        channel = commands.TextChannelConverter().convert(ctx, given.content)
                    except commands.BadArgument:
                        continue
                    else:
                        break
                if channel is None:
                    continue
                await module.module_config.set_raw("_log_channel", value=getattr(channel, "id", None))
                async with ConfirmMenu(ctx, colour=discord.Color.blurple(),
                                       message=i18n("Would you like to setup logging options for module **{}**?")
                                       .format(module.friendly_name))\
                        as setup_opts:
                    if setup_opts:
                        tmp = await ctx.send(embed=await module.config_embed())
                        resp = await prompt(ctx, content=i18n("Please respond with a space-separated list of options "
                                                              "you would like to enable"),
                                            delete_messages=True, timeout=90)
                        if resp:
                            await module.toggle_options(*str(resp.content).split(" "))
                        await tmp.delete()
                    await fmt(ctx, info(i18n("You can setup the options for this module later with "
                                             "`{prefix}logset module {module}`.")),
                              module=module_name, delete_after=15.0)
        await ctx.send(tick(i18n("You're all done!")))

    @logset.command(name="webhook")
    @commands.bot_has_permissions(manage_webhooks=True)
    async def logset_webhook(self, ctx: RedContext, module: str, channel: discord.TextChannel = None):
        """Setup a module to log via a webhook

        This cannot be combined with a conventional log channel set with `[p]logset channel`

        Previously created webhooks that are then unregistered are not cleaned up
        by this command, and have to be removed manually.
        """
        module = get_module(module, guild=ctx.guild)
        if module is None:
            await ctx.send(warning(i18n("That module could not be found")))
            return

        if not await module.can_modify_settings(ctx.author):
            await ctx.send(error(i18n("You aren't authorized to modify this module's settings")))
            return

        await module.module_config.set_raw("_log_channel", value=None)
        if channel is None:
            await module.module_config.set_raw("_webhook", value=None)
            await ctx.send(tick(i18n("Any previously set webhook for module **{module}** has been cleared.")
                                .format(module=module.friendly_name)))
            return

        try:
            webhooks = await channel.webhooks()  # type: List[discord.Webhook]
        except discord.Forbidden:
            await ctx.send(error(i18n("I'm not authorized to manage webhooks in that channel")))
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
        await ctx.send(tick(i18n("Module **{module}** will now log to {channel} via webhook.")
                            .format(module=module.friendly_name, channel=channel.mention)))

    @logset.command(name="channel")
    async def logset_channel(self, ctx: RedContext, module: str, channel: discord.TextChannel = None):
        """Set the log channel for a module

        Passing no log channel effectively acts as disabling the module
        """
        module = get_module(module, guild=ctx.guild)
        if module is None:
            await ctx.send(warning(i18n("That module could not be found")))
            return
        if not await module.can_modify_settings(ctx.author):
            await ctx.send(error(i18n("You aren't authorized to modify this module's settings")))
            return
        if channel and not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send(warning(i18n("I'm not able to send messages in that channel")))
            return
        await module.module_config.set_raw("_log_channel", value=getattr(channel, "id", None))
        await module.module_config.set_raw("_webhook", value=None)
        if channel:
            await ctx.send(tick(i18n("Module **{module}** will now log to {channel}")
                                .format(module=module.friendly_name, channel=channel.mention)))
        else:
            await ctx.send(tick(i18n("The log channel for module **{module}** has been cleared")
                                .format(module=module.friendly_name)))

    @logset.command(name="modules", aliases=["list"])
    async def logset_modules(self, ctx: RedContext):
        """List all available modules"""
        modules = []
        for module in all_modules.values():
            if not await module(ctx.guild).can_modify_settings(ctx.author):
                continue
            # > expected type str, got type property instead
            # > ???????
            # noinspection PyTypeChecker
            modules.append("{} \N{EM DASH} {}".format(bold(module.friendly_name), inline(str(module.name))))

        await ctx.send(info(i18n("Available modules:\n\n{modules}").format(modules="\n".join(modules))))

    @logset.command(name="module")
    async def logset_module(self, ctx: RedContext, module: str, *settings: str):
        """Get or set a module's settings"""
        module = get_module(module, guild=ctx.guild)
        if module is None:
            await ctx.send(warning(i18n("That module could not be found")))
            return
        if not await module.can_modify_settings(ctx.author):
            await ctx.send(error(i18n("You aren't authorized to modify this module's settings")))
            return
        if not settings:
            await ctx.send(embed=await module.config_embed())
        else:
            await module.toggle_options(*settings)
            await ctx.send(content=tick(i18n("Updated settings for module **{}**").format(module.friendly_name)),
                           embed=await module.config_embed())

    @logset.command(name="reset")
    async def logset_reset(self, ctx: RedContext):
        """Reset the server's log settings"""
        if await ConfirmMenu(ctx, i18n("Are you sure you want to reset this server's log settings?"),
                             colour=discord.Colour.red()):
            await self.config.guild(ctx.guild).set(self.defaults_guild)
            await ctx.send(embed=discord.Embed(
                description=i18n("Server log settings have been reset."),
                colour=discord.Colour.green()))
        else:
            await ctx.send(embed=discord.Embed(description=i18n("Okay then."), colour=discord.Colour.gold()))

    ####################
    #   Ignore Mgnt    #
    ####################

    # Welcome to the Sea of Bad Ideas™, please enjoy your stay.

    logset_ignore = cmd_group('ignore', parent=logset, help=i18n("Manage the servers ignore lists"))

    ignore_guild = ignore_handler(name='server', aliases=['guild'], parent=logset_ignore, converters=[],
                                  conf_opt='guild', help=i18n("Toggle the current server's ignore status"))

    # Channels
    ignore_channel = cmd_group('channel', parent=logset_ignore, help=i18n("Manage the channel ignore list"))
    ignore_channel_add = ignore_handler(parent=ignore_channel, help=i18n("Ignore a given channel"),
                                        conf_opt="channels",
                                        converters=[commands.TextChannelConverter, commands.VoiceChannelConverter,
                                                    commands.CategoryChannelConverter])
    ignore_channel_remove = ignore_handler(parent=ignore_channel, help=i18n("Unignore a given channel"),
                                           conf_opt="channels", remove=True,
                                           converters=[commands.TextChannelConverter, commands.VoiceChannelConverter,
                                                       commands.CategoryChannelConverter])

    # Members
    ignore_member = cmd_group('member', parent=logset_ignore, help=i18n("Manage the member ignore list"))
    ignore_member_add = ignore_handler(conf_opt='members', parent=ignore_member, help=i18n("Ignore a given member"),
                                       converters=[commands.MemberConverter])
    ignore_member_remove = ignore_handler(conf_opt='members', parent=ignore_member, remove=True,
                                          help=i18n("Unignore a given member"), converters=[commands.MemberConverter])

    # Roles
    ignore_role = cmd_group('role', parent=logset_ignore, help=i18n("Manage the role ignore list"))
    ignore_role_add = ignore_handler(conf_opt='roles', parent=ignore_role, help=i18n("Ignore a given role"),
                                     converters=[commands.RoleConverter])
    ignore_role_remove = ignore_handler(conf_opt='roles', parent=ignore_role, help=i18n("Unignore a given role"),
                                        converters=[commands.RoleConverter], remove=True)

    # Member Roles
    ignore_mrole = cmd_group('memberrole', aliases=['mrole'], help=i18n("Manage the member role ignore list"),
                             parent=logset_ignore)
    ignore_mrole_add = ignore_handler(conf_opt='member_roles', converters=[commands.RoleConverter],
                                      parent=ignore_mrole, help=i18n("Add a member role to the ignore list"))
    ignore_mrole_remove = ignore_handler(conf_opt='member_roles', converters=[commands.RoleConverter], remove=True,
                                         parent=ignore_mrole, help=i18n("Add a member role to the ignore list"))

    ###################
    #    Listeners    #
    ###################

    async def on_message_delete(self, message: discord.Message):
        if not getattr(message, "guild", None):
            return
        module = get_module("message", message.guild)
        await module.log("delete", message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not getattr(after, "guild", None):
            return
        module = get_module("message", after.guild)
        await module.log("edit", before, after)

    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent):
        channel = self.bot.get_channel(payload.channel_id)  # type: discord.TextChannel
        try:
            guild = channel.guild  # type: discord.Guild
            if guild is None:
                return
        except AttributeError:
            return
        module = get_module("message", guild)
        await module.log("bulk_delete", channel, payload.message_ids)

    async def on_member_join(self, member: discord.Member):
        module = get_module("member", member.guild)
        await module.log("join", member)

    async def on_member_leave(self, member: discord.Member):
        module = get_module("member", member.guild)
        await module.log("leave", member)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        module = get_module("member", after.guild)
        await module.log("update", before, after)

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        module = get_module("channel", channel.guild)
        await module.log("create", channel)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        module = get_module("channel", channel.guild)
        await module.log("delete", channel)

    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        module = get_module("channel", after.guild)
        await module.log("update", before, after)

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        if not hasattr(member, "guild"):
            return
        module = get_module("voice", member.guild)
        await module.log("update", before, after, member)

    async def on_guild_role_create(self, role: discord.Role):
        module = get_module("role", role.guild)
        await module.log("create", role)

    async def on_guild_role_delete(self, role: discord.Role):
        module = get_module("role", role.guild)
        await module.log("delete", role)

    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        module = get_module("role", after.guild)
        await module.log("update", before, after)

    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        module = get_module("guild", after)
        await module.log("update", before, after)
