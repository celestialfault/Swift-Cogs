import contextlib
from typing import List, Type

import discord
from discord.raw_models import RawBulkMessageDeleteEvent
from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import cog_i18n
from redbot.core.utils.chat_formatting import bold, info, inline, warning

from cog_shared.swift_libs import (
    confirm,
    PaginatedMenu,
    cmd_group,
    cmd_help,
    fi18n,
    tick,
    prompt,
    Page,
    PostAction,
)
from logs.core import Module, get_module, i18n, log_event, config
from logs.core.module import load, log, unload
from logs.modules import DummyModule, modules as all_modules


def ignore_handler(
    *,
    parent: commands.Group = commands,
    converters: List[Type[commands.Converter]],
    conf_opt: str,
    remove: bool = False,
    **kwargs
):
    # Yes: This is probably the worst idea that's been implemented yet in this entire cog to date.
    # But I mean, hey; it sure beats the dozen+ commands with functionally the exact same code
    # that was here before.
    name = kwargs.pop("name", "add" if remove is False else "remove")

    # noinspection PyUnusedLocal
    async def _command(self, ctx: commands.Context, *, item):
        new_item = ...
        for converter in converters:
            with contextlib.suppress(commands.BadArgument):
                new_item = await converter().convert(ctx, item)
                break
        if new_item is ...:
            raise commands.BadArgument
        item = getattr(item, "id", item)
        # noinspection PyTypeChecker
        async with DummyModule().config.guild(ctx.guild).ignore.get_attr(conf_opt)() as ignored:
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
            log.debug(
                "{} {!r} to/from {!r} {} ignore list".format(name, new_item, ctx.guild, conf_opt)
            )
            await ctx.tick()

    if conf_opt == "guild":
        # noinspection PyUnusedLocal
        async def _command(self, ctx: commands.Context, toggle: bool = None):  # noqa
            if toggle is None:
                # noinspection PyTypeChecker
                toggle = not await DummyModule().config.guild(ctx.guild).ignore.guild()
            # noinspection PyTypeChecker
            await DummyModule().config.guild(ctx.guild).ignore.guild.set(toggle)
            await ctx.send(
                tick(
                    i18n("Now ignoring the current server")
                    if toggle
                    else i18n("No longer ignoring the current server")
                )
            )

    return parent.command(name=name, **kwargs)(_command)


async def retrieve_module(ctx: commands.Context, module_name: str):
    module = get_module(module_name, guild=ctx.guild)
    if module is None:
        raise commands.BadArgument
    if not await module.can_modify_settings(ctx.author):
        raise commands.CheckFailure
    return module


async def retrieve_all_modules(ctx: commands.Context) -> List[Module]:
    """Returns all modules the given member can modify"""
    modules = []
    for module in all_modules.values():
        module = module(guild=ctx.guild)
        if not await module.can_modify_settings(ctx.author):
            continue
        modules.append(module)
    return modules


# noinspection PyMethodMayBeStatic
@cog_i18n(i18n)
class Logs:
    """Log anything and everything that happens in your server"""

    __author__ = "odinair <odinair@odinair.xyz>"

    def __init__(self, bot: Red):
        self.bot = bot
        load(self.bot)

    def __unload(self):
        unload()

    @commands.group(name="logset")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def logset(self, ctx: commands.Context):
        """Manage log settings"""
        await cmd_help(ctx)

    @logset.command(name="setup")
    async def logset_setup(self, ctx: commands.Context):
        """Quick-start for logging settings"""
        modules = await retrieve_all_modules(ctx)

        async def converter(pg: Page):
            return discord.Embed(
                description=i18n(
                    "**{mod.friendly_name} Settings**\nLogging to: {destination}\n\n"
                    "\N{GEAR} \N{EM DASH} Update module log settings\n"
                    "\N{HEADPHONE} \N{EM DASH} Set log channel\n"
                    "\N{CROSS MARK} \N{EM DASH} Close menu"
                ).format(
                    mod=pg.data,
                    destination=getattr(
                        await pg.data.log_destination(), "mention", i18n("No log channel setup")
                    ),
                )
            ).set_author(
                name="Logs Setup", icon_url=ctx.guild.icon_url
            ).set_footer(
                text=i18n("Module {0.current} out of {0.total}").format(pg)
            )

        last_page = 0
        while True:
            result = await PaginatedMenu(
                ctx=ctx,
                actions={
                    "settings": "\N{GEAR}", "channel": "\N{HEADPHONE}", "close": "\N{CROSS MARK}"
                },
                pages=modules,
                converter=converter,
                wrap_around=True,
                page=last_page,
            ).prompt(
                post_action=PostAction.NO_ACTION
            )
            module = result.page
            last_page = modules.index(module)

            try:
                await result.menu.message.delete()
                result.menu.message = None
            except (AttributeError, discord.HTTPException):
                pass

            if result.timed_out or result == "close":
                break

            if result == "settings":
                tmp = await ctx.send(embed=await module.config_embed())
                resp = await prompt(
                    ctx,
                    content=i18n(
                        "Please respond with a space-separated list of options you would like "
                        "to enable."
                    ),
                    delete_messages=True,
                    timeout=90,
                )
                if resp:
                    await module.toggle_options(*str(resp.content).split(" "))
                await tmp.delete()

            elif result == "channel":
                try:
                    channel = commands.TextChannelConverter().convert(
                        ctx,
                        (
                            await prompt(
                                ctx,
                                content=i18n("What channel would you like to log to?"),
                                timeout=90,
                                delete_messages=True,
                            )
                        ).content,
                    )
                except (commands.BadArgument, AttributeError):
                    continue
                else:
                    if channel is None:
                        continue
                    await module.module_config.set_raw(
                        "_log_channel", value=getattr(channel, "id", None)
                    )

    @logset.command(name="channel")
    async def logset_channel(
        self, ctx: commands.Context, module: str, channel: discord.TextChannel = None
    ):
        """Set the log channel for a module

        Passing no log channel effectively acts as disabling the module
        """
        module = await retrieve_module(ctx, module)
        if channel and not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send(warning(i18n("I'm not able to send messages in that channel")))
            return
        await module.module_config.set_raw("_log_channel", value=getattr(channel, "id", None))
        if channel:
            await ctx.send(
                tick(
                    i18n("Module **{module}** will now log to {channel}").format(
                        module=module.friendly_name, channel=channel.mention
                    )
                )
            )
        else:
            await ctx.send(
                tick(
                    i18n("The log channel for module **{module}** has been cleared").format(
                        module=module.friendly_name
                    )
                )
            )

    @logset.command(name="modules", aliases=["list"])
    async def logset_modules(self, ctx: commands.Context):
        """List all available modules"""
        modules = [
            "{} \N{EM DASH} {}".format(bold(module.friendly_name), inline(str(module.name)))
            for module in await retrieve_all_modules(ctx)
        ]

        await ctx.send(
            info(i18n("Available modules:\n\n{modules}").format(modules="\n".join(modules)))
        )

    @logset.command(name="module")
    async def logset_module(self, ctx: commands.Context, module: str, *settings: str):
        """Get or set a module's settings"""
        module = await retrieve_module(ctx, module)
        if not settings:
            await ctx.send(embed=await module.config_embed())
        else:
            await module.toggle_options(*settings)
            await ctx.send(
                content=tick(
                    i18n("Updated settings for module **{}**").format(module.friendly_name)
                ),
                embed=await module.config_embed(),
            )

    @logset.command(name="reset")
    async def logset_reset(self, ctx: commands.Context):
        """Reset the server's log settings"""
        if await confirm(
            ctx, content=warning(i18n("Are you sure you want to reset this server's log settings?"))
        ):
            await config.guild(ctx.guild).clear()
            await ctx.send(tick(i18n("Server log settings have been reset.")))
        else:
            await ctx.send(i18n("Okay then."))

    ####################
    #   Ignore Mgnt    #
    ####################

    # Welcome to the Sea of Bad Ideas™, please enjoy your stay.

    # explanation for the following series of fi18n calls:
    # `fi18n` is added as a keyword function when calling redgettext via
    # `swift_libs/scripts/gen_locales.py`, and all fi18n does is just returns the
    # input string, as a means to get red's dpy command wrapper to translate
    # help strings for us

    logset_ignore = cmd_group(
        "ignore", parent=logset, help=fi18n("Manage the servers ignore lists")
    )

    ignore_guild = ignore_handler(
        name="server",
        aliases=["guild"],
        parent=logset_ignore,
        converters=[],
        conf_opt="guild",
        help=fi18n("Toggle the current server's ignore status"),
    )

    # Channels
    ignore_channel = cmd_group(
        "channel", parent=logset_ignore, help=fi18n("Manage the channel ignore list")
    )
    ignore_channel_add = ignore_handler(
        parent=ignore_channel,
        help=fi18n("Ignore a given channel"),
        conf_opt="channels",
        converters=[
            commands.TextChannelConverter,
            commands.VoiceChannelConverter,
            commands.CategoryChannelConverter,
        ],
    )
    ignore_channel_remove = ignore_handler(
        parent=ignore_channel,
        help=fi18n("Unignore a given channel"),
        conf_opt="channels",
        remove=True,
        converters=[
            commands.TextChannelConverter,
            commands.VoiceChannelConverter,
            commands.CategoryChannelConverter,
        ],
    )

    # Members
    ignore_member = cmd_group(
        "member", parent=logset_ignore, help=fi18n("Manage the member ignore list")
    )
    ignore_member_add = ignore_handler(
        conf_opt="members",
        parent=ignore_member,
        help=fi18n("Ignore a given member"),
        converters=[commands.MemberConverter],
    )
    ignore_member_remove = ignore_handler(
        conf_opt="members",
        parent=ignore_member,
        remove=True,
        help=fi18n("Unignore a given member"),
        converters=[commands.MemberConverter],
    )

    # Roles
    ignore_role = cmd_group("role", parent=logset_ignore, help=fi18n("Manage the role ignore list"))
    ignore_role_add = ignore_handler(
        conf_opt="roles",
        parent=ignore_role,
        help=fi18n("Ignore a given role"),
        converters=[commands.RoleConverter],
    )
    ignore_role_remove = ignore_handler(
        conf_opt="roles",
        parent=ignore_role,
        help=fi18n("Unignore a given role"),
        converters=[commands.RoleConverter],
        remove=True,
    )

    # Member Roles
    ignore_mrole = cmd_group(
        "memberrole",
        aliases=["mrole"],
        help=fi18n("Manage the member role ignore list"),
        parent=logset_ignore,
    )
    ignore_mrole_add = ignore_handler(
        conf_opt="member_roles",
        converters=[commands.RoleConverter],
        parent=ignore_mrole,
        help=fi18n("Add a member role to the ignore list"),
    )
    ignore_mrole_remove = ignore_handler(
        conf_opt="member_roles",
        converters=[commands.RoleConverter],
        remove=True,
        parent=ignore_mrole,
        help=fi18n("Add a member role to the ignore list"),
    )

    ###################
    #    Listeners    #
    ###################

    async def on_message_delete(self, message: discord.Message):
        if not hasattr(message, "guild") or message.guild is None:
            return
        await log_event("message", "delete", message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not hasattr(after, "guild") or after.guild is None:
            return
        await log_event("message", "edit", before, after)

    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent):
        channel: discord.TextChannel = self.bot.get_channel(payload.channel_id)
        if not hasattr(channel, "guild") or channel.guild is None:
            return
        await log_event("message", "bulk_delete", channel, payload.message_ids)

    async def on_member_join(self, member: discord.Member):
        await log_event("member", "join", member)

    async def on_member_leave(self, member: discord.Member):
        await log_event("member", "leave", member)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        await log_event("member", "update", before, after)

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        await log_event("channel", "create", channel)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await log_event("channel", "delete", channel)

    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        await log_event("channel", "update", before, after)

    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        if not hasattr(member, "guild"):
            return
        await log_event("voice", "update", before, after, member)

    async def on_guild_role_create(self, role: discord.Role):
        await log_event("role", "create", role)

    async def on_guild_role_delete(self, role: discord.Role):
        await log_event("role", "delete", role)

    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        await log_event("role", "update", before, after)

    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        await log_event("guild", "update", before, after)
