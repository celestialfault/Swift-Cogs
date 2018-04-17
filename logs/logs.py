from aiohttp import ClientSession
from typing import List, Optional

import discord
from discord.ext import commands
from discord.raw_models import RawBulkMessageDeleteEvent

from redbot.core import checks, Config
from redbot.core.bot import Red, RedContext
from redbot.core.utils.chat_formatting import warning, info, error, escape, inline, bold

from logs.core import Module, get_module, _
from logs.modules import all_modules

from cog_shared.odinair_libs import tick, cmd_help, fmt, ConfirmMenu, prompt


# noinspection PyMethodMayBeStatic
class Logs:
    """Log anything and everything that happens in your server"""

    __author__ = "odinair <odinair@odinair.xyz>"

    defaults_guild = {
        **{
            all_modules[x].name: {
                "_log_channel": None,
                "_webhook": None,
                **all_modules[x](guild=None).defaults
            } for x in all_modules
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
            async with ConfirmMenu(ctx, message=_("Would you like to enable the **{}** module?").format(
                    module.friendly_name)) as result:
                await module.module_config.clear()
                if not result:
                    continue
                channel = None  # type: Optional[discord.TextChannel]
                while channel is None:
                    given = await prompt(ctx, content=_("What channel would you like to log to?"), timeout=90,
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
                                       message=_("Would you like to setup logging options for module **{}**?")
                                       .format(module.friendly_name))\
                        as setup_opts:
                    if setup_opts:
                        tmp = await ctx.send(embed=await module.config_embed())
                        resp = await prompt(ctx, content=_("Please respond with a space-separated list of options you "
                                                           "would like to enable"), delete_messages=True, timeout=90)
                        if resp:
                            await module.toggle_options(*str(resp.content).split(" "))
                        await tmp.delete()
                    await fmt(ctx, info(_("You can setup the options for this module later with "
                                          "`{prefix}logset module {module}`.")),
                              module=module_name, delete_after=15.0)
        await ctx.send(tick(_("You're all done!")))

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
            await ctx.send(warning(_("That module could not be found")))
            return

        await module.module_config.set_raw("_log_channel", value=None)
        if channel is None:
            await module.module_config.set_raw("_webhook", value=None)
            await ctx.send(tick(_("Any previously set webhook for module **{module}** has been cleared.")
                                .format(module=module.friendly_name)))
            return

        try:
            webhooks = await channel.webhooks()  # type: List[discord.Webhook]
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
        await ctx.send(tick(_("Module **{module}** will now log to {channel} via webhook.")
                            .format(module=module.friendly_name, channel=channel.mention)))

    @logset.command(name="channel")
    async def logset_channel(self, ctx: RedContext, module: str, channel: discord.TextChannel = None):
        """Set the log channel for a module

        Passing no log channel effectively acts as disabling the module
        """
        module = get_module(module, guild=ctx.guild)
        if module is None:
            await ctx.send(warning(_("That module could not be found")))
            return
        if channel and not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send(warning(_("I'm not able to send messages in that channel")))
            return
        await module.module_config.set_raw("_log_channel", value=getattr(channel, "id", None))
        await module.module_config.set_raw("_webhook", value=None)
        if channel:
            await ctx.send(tick(_("Module **{module}** will now log to {channel}")
                                .format(module=module.friendly_name, channel=channel.mention)))
        else:
            await ctx.send(tick(_("The log channel for module **{module}** has been cleared")
                                .format(module=module.friendly_name)))

    @logset.command(name="modules", aliases=["list"])
    async def logset_modules(self, ctx: RedContext):
        """List all available modules"""
        modules = []
        for module in all_modules:
            module = all_modules[module]
            # > expected type str, got type property instead
            # > ???????
            # noinspection PyTypeChecker
            modules.append("{} \N{EM DASH} {}".format(bold(module.friendly_name), inline(str(module.name))))

        await ctx.send(info(_("Available modules:\n\n{modules}").format(modules="\n".join(modules))))

    @logset.command(name="module")
    async def logset_module(self, ctx: RedContext, module: str, *settings: str):
        """Get or set a module's settings"""
        module = get_module(module, guild=ctx.guild)
        if module is None:
            await ctx.send(warning(_("That module could not be found")))
            return
        if not settings:
            await ctx.send(embed=await module.config_embed())
        else:
            await module.toggle_options(*settings)
            await ctx.send(content=tick(_("Updated settings for module **{}**").format(module.friendly_name)),
                           embed=await module.config_embed())

    @logset.command(name="reset")
    async def logset_reset(self, ctx: RedContext):
        """Reset the guild's log settings"""
        if await ConfirmMenu(ctx, _("Are you sure you want to reset this guild's log settings?"),
                             colour=discord.Colour.red()).prompt():
            await self.config.guild(ctx.guild).set(self.defaults_guild)
            await ctx.send(embed=discord.Embed(
                description=_("Guild log settings have been reset."),
                colour=discord.Colour.green()))
        else:
            await ctx.send(embed=discord.Embed(description=_("Okay then."), colour=discord.Colour.gold()))

    ###################
    #   Ignore Cmd    #
    ###################

    @logset.group(name="ignore")
    async def logset_ignore(self, ctx: RedContext):
        """Add items to the guild logging ignore list"""
        await cmd_help(ctx, "ignore")

    @logset_ignore.command(name="channel")
    async def ignore_channel(self, ctx: RedContext, *,
                             channel: discord.TextChannel or discord.VoiceChannel or discord.CategoryChannel = None):
        """Add a channel or category to the guild ignore list

        Any channels in a category that is ignored are also implicitly ignored

        `channel` defaults to the current channel
        """
        if channel is None:
            channel = ctx.channel
        async with self.config.guild(ctx.guild).ignore.channels() as ignored:
            if channel.id in ignored:
                await ctx.send(warning(_("That channel is already being ignored")))
                return
            ignored.append(channel.id)
            if not isinstance(channel, discord.CategoryChannel):
                await ctx.send(tick(_("The channel {channel} is now ignored from logging")
                                    .format(channel=channel.mention)))
            else:
                await ctx.send(tick(_("The category {channel} and it's subchannels are now ignored from logging")
                                    .format(channel=channel.mention)))

    @logset_ignore.command(name="member")
    async def ignore_member(self, ctx: RedContext, *, member: discord.Member):
        """Add a member to the guild ignore list"""
        async with self.config.guild(ctx.guild).ignore.members() as ignored:
            if member.id in ignored:
                await ctx.send(warning(_("That member is already being ignored")))
                return
            ignored.append(member.id)
            await ctx.send(tick(_("Member **{member}** is now ignored from logging").format(member=member)))

    @logset_ignore.command(name="role")
    async def ignore_role(self, ctx: RedContext, *, role: discord.Role):
        """Add a role to the guild ignore list

        This only ignores roles themselves from being logged with the Role module,
        and not members with the role, nor members being given / having the role revoked.
        To ignore members with a given role, please see `[p]help logset ignore memberrole`
        """
        async with self.config.guild(ctx.guild).ignore.roles() as ignored:
            if role.id in ignored:
                await ctx.send(warning(_("That role is already being ignored")))
                return
            ignored.append(role.id)
            await ctx.send(tick(_("The role **{role}** is now ignored from logging")
                                .format(role=escape(str(role), mass_mentions=True, formatting=True))))

    @logset_ignore.command(name="memberrole")
    async def ignore_memberrole(self, ctx: RedContext, *, role: discord.Role):
        """Add a member role to the guild ignore list

        This is not the same as regular role ignoring, as this ignores members
        who have the given role, instead of ignoring the role from logging via
        the role module.
        """
        async with self.config.guild(ctx.guild).ignore.member_roles() as ignored:
            if role.id in ignored:
                await ctx.send(warning(_("That role is already being ignored")))
                return
            ignored.remove(role.id)
            await ctx.send(tick(_("Members with the role **{role}** are no longer ignored from logging")
                                .format(role=escape(str(role), mass_mentions=True, formatting=True))))

    @logset_ignore.command(name="guild")
    async def ignore_guild(self, ctx: RedContext):
        """Ignore the current guild entirely"""
        await self.config.guild(ctx.guild).ignore.guild.set(True)
        await ctx.send(tick(_("Now ignoring the current guild")))

    ###################
    #  Unignore Cmd   #
    ###################

    @logset.group(name="unignore")
    async def logset_unignore(self, ctx: RedContext):
        """Remove items from the guild logging ignore list"""
        await cmd_help(ctx, "unignore")

    @logset_unignore.command(name="channel")
    async def unignore_channel(self, ctx: RedContext, *,
                               channel: discord.TextChannel or discord.VoiceChannel or discord.CategoryChannel = None):
        """Remove a channel or category from the guild ignore list"""
        if channel is None:
            channel = ctx.channel
        async with self.config.guild(ctx.guild).ignore.channels() as ignored:
            if channel.id not in ignored:
                await ctx.send(warning(_("That channel isn't currently being ignored")))
                return
            ignored.remove(channel.id)
            if not isinstance(channel, discord.CategoryChannel):
                await ctx.send(tick(_("The channel {channel} is no longer ignored from logging")
                                    .format(channel=channel.mention)))
            else:
                await ctx.send(tick(_("The category {channel} and it's subchannels are no longer ignored from logging")
                                    .format(channel=channel.mention)))

    @logset_unignore.command(name="member")
    async def unignore_member(self, ctx: RedContext, *, member: discord.Member):
        """Remove a member from the guild ignore list"""
        async with self.config.guild(ctx.guild).ignore.members() as ignored:
            if member.id not in ignored:
                await ctx.send(warning(_("That member isn't currently being ignored")))
                return
            ignored.remove(member.id)
            await ctx.send(tick(_("Member **{member}** is no longer ignored from logging").format(member=member)))

    @logset_unignore.command(name="role")
    async def unignore_role(self, ctx: RedContext, *, role: discord.Role):
        """Remove a role from the guild ignore list"""
        async with self.config.guild(ctx.guild).ignore.roles() as ignored:
            if role.id not in ignored:
                await ctx.send(warning(_("That role isn't currently being ignored")))
                return
            ignored.remove(role.id)
            await ctx.send(tick(_("The role **{role}** is no longer ignored from logging")
                                .format(role=escape(str(role), mass_mentions=True, formatting=True))))

    @logset_unignore.command(name="memberrole")
    async def unignore_memberrole(self, ctx: RedContext, *, role: discord.Role):
        """Remove a member role from the guild ignore list"""
        async with self.config.guild(ctx.guild).ignore.member_roles() as ignored:
            if role.id not in ignored:
                await ctx.send(warning(_("That role isn't currently being ignored")))
                return
            ignored.remove(role.id)
            await ctx.send(tick(_("Members with the role **{role}** are no longer ignored from logging")
                                .format(role=escape(str(role), mass_mentions=True, formatting=True))))

    @logset_unignore.command(name="guild")
    async def unignore_guild(self, ctx: RedContext):
        """Stop ignoring the current guild entirely"""
        await self.config.guild(ctx.guild).ignore.guild.set(False)
        await ctx.send(tick(_("No longer ignoring the current guild")))

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
