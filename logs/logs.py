from typing import Sequence, Dict, List

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.config import Group
from redbot.core.utils.chat_formatting import warning, escape, bold

from logs.guildlog import GuildLog, LogType
from logs import types as log_types
# noinspection PyProtectedMember
from logs.i18n import _

from odinair_libs.config import group_toggle
from odinair_libs.formatting import tick, normalize, chunks, cmd_help
from odinair_libs.menus import confirm, paginate


# noinspection PyShadowingNames
class Logs:
    """Log anything and everything that happens in your server"""

    __author__ = "odinair <odinair@odinair.xyz>"
    __version__ = "0.1.0"

    _descriptions = {x.name: x.descriptions for x in log_types.iterable}
    defaults_guild = {
        "log_channels": {
            "roles": None,
            "server": None,
            "messages": None,
            "members": None,
            "channels": None,
            "voice": None
        },
        "roles": {
            "create": False,
            "delete": False,
            "name": False,
            "permissions": False,
            "hoist": False,
            "mention": False,
            "position": False,
            "colour": False
        },
        "server": {
            "name": False,
            "2fa": False,
            "verification": False,
            "afk": False,
            "region": False,
            "content_filter": False,
            "owner": False
        },
        "messages": {
            "edit": False,
            "delete": False
        },
        "members": {
            "join": False,
            "leave": False,
            "name": False,
            "discriminator": False,
            "nickname": False,
            "roles": False
        },
        "channels": {
            "create": False,
            "delete": False,
            "name": False,
            "topic": False,
            "position": False,
            "category": False,
            "bitrate": False,
            "user_limit": False
        },
        "voice": {
            "channel": False,
            "selfmute": False,
            "servermute": False,
            "selfdeaf": False,
            "serverdeaf": False
        },
        "ignored": False
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=35908345472, force_registration=True)
        self.config.register_guild(**self.defaults_guild)
        self.config.register_member(ignored=False)
        self.config.register_channel(ignored=False)
        self.config.register_role(ignored=False)
        self._guilds = {}

    async def get_guild_log(self, guild: discord.Guild) -> GuildLog:
        if guild.id not in self._guilds:
            self._guilds[guild.id] = GuildLog(guild, cog=self)
            await self._guilds[guild.id].init()
        return self._guilds[guild.id]

    @commands.group(name="logset")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def logset(self, ctx: RedContext):
        """Manage log settings"""
        await self.get_guild_log(ctx.guild)  # the return value is intentionally ignored here
        await cmd_help(ctx, "")

    @logset.group(name="logchannel", invoke_without_command=True)
    async def logset_logchannel(self, ctx: RedContext, channel: discord.TextChannel, *log_types: str):
        """Manage the guild's log channels

        Available log types:

        **server**, **members**, **roles**, **messages**, **channels**, **voice**

        `all` is also accepted to set all of the above log types at once
        """
        if not log_types:
            await ctx.send_help()
            return
        guild = await self.get_guild_log(ctx.guild)
        if any([x for x in log_types if x.lower() not in guild.guild_config.log_channels.defaults]) \
                and "all" not in log_types:
            await ctx.send_help()
            return
        async with guild.guild_config.log_channels() as channels:
            if "all" in log_types:
                defaults = guild.guild_config.log_channels.defaults
                channels.update({x: channel.id for x in defaults})
                await ctx.send(tick(_("Set all log channels to {}").format(channel.mention)))
            else:
                formatted_types = ", ".join([bold(x.title()) for x in log_types])
                await ctx.send(tick(_("Set log channels for types {} to {}").format(formatted_types, channel.mention)))
        await guild.reload_settings()

    @logset_logchannel.command(name="clear")
    async def logchannel_clear(self, ctx: RedContext, *log_types: str):
        """Clear log channels for specific types or all log types

        If no log types are passed, all log channels are cleared
        """
        guild = await self.get_guild_log(ctx.guild)
        if any([x for x in log_types if x.lower() not in guild.guild_config.log_channels.defaults]):
            await ctx.send_help()
            return
        if not log_types:
            if not await confirm(ctx, message=_("Are you sure you want to clear all log channels?")):
                await ctx.send_help()
                return
        async with guild.guild_config.log_channels() as channels:
            if not log_types:
                channels.update(guild.guild_config.log_channels.defaults)
                await ctx.send(tick(_("Cleared all log channels")))
            else:
                channels.update({x: None for x in log_types})
                formatted_types = ", ".join([bold(x.title()) for x in log_types])
                await ctx.send(tick(_("Cleared log channels for log types {}").format(formatted_types)))
        await guild.reload_settings()

    @logset.command(name="server", aliases=["guild"])
    async def logset_guild(self, ctx: RedContext, *settings):
        """Set server update logging

        Available log settings:

        **2fa** — Server two factor authentication requirement
        **verification** — Server verification level
        **name** — Server name
        **owner** — Server ownership
        **afk** — Server AFK channel and timeout
        **region** — Server voice region
        **content_filter** — Explicit content filter
        """
        await handle_group(ctx, types=settings, settings=self.config.guild(ctx.guild).server, setting_type="server",
                           slots=self._descriptions["server"].keys(), descriptions=self._descriptions["server"])
        await (await self.get_guild_log(ctx.guild)).reload_settings()

    @logset.command(name="channel")
    async def logset_channel_update(self, ctx: RedContext, *settings):
        """Manage channel logging

        Available log settings:

        **create** — Channel creation
        **delete** — Channel deletion
        **name** — Channel name
        **topic** — Channel topic
        **category** — Channel category
        **bitrate** — Voice channel bitrate
        **user_limit** — Voice channel user limit
        **position** — Channel position - this option may result in log spam!
        """
        await handle_group(ctx, types=settings, settings=self.config.guild(ctx.guild).channels, setting_type="channel",
                           slots=self._descriptions["channels"].keys(), descriptions=self._descriptions["channels"])
        await (await self.get_guild_log(ctx.guild)).reload_settings()

    @logset.command(name="message")
    async def logset_message(self, ctx: RedContext, *settings):
        """Manage message logging

        Available log settings:

        **edit** — Message edits
        **delete** — Message deletion
        """
        await handle_group(ctx, types=settings, settings=self.config.guild(ctx.guild).messages, setting_type="message",
                           slots=["edit", "delete"], descriptions=self._descriptions["messages"])
        await (await self.get_guild_log(ctx.guild)).reload_settings()

    @logset.command(name="member")
    async def logset_member(self, ctx: RedContext, *settings: str):
        """Manage member logging

        Available log settings:

        **join** — Member joining
        **leave** — Member leaving
        **name** — Member username
        **discriminator** — Member discriminator
        **nickname** — Member nickname
        **roles** — Member roles
        """
        await handle_group(ctx, types=settings, settings=self.config.guild(ctx.guild).members, setting_type="member",
                           slots=self._descriptions["members"].keys(), descriptions=self._descriptions["members"])
        await (await self.get_guild_log(ctx.guild)).reload_settings()

    @logset.command(name="role")
    async def logset_role_update(self, ctx: RedContext, *settings):
        """Manage role logging

        Available log settings:

        **create** — Role creation
        **delete** — Role deletion
        **name** — Role name updates
        **hoist** — Role hoist status updates
        **mention** — Role mentionable status updates
        **permissions** — Role permission updates
        **colour** — Role colour updates
        **position** — Role position updates - this option may result in log spam!
        """
        await handle_group(ctx, types=settings, settings=self.config.guild(ctx.guild).roles, setting_type="role",
                           slots=self._descriptions["roles"].keys(), descriptions=self._descriptions["roles"])
        await (await self.get_guild_log(ctx.guild)).reload_settings()

    @logset.command(name="voice")
    async def logset_voice(self, ctx: RedContext, *settings):
        """Manage voice status logging

        Available log settings:

        **channel** — Member voice channel joining, leaving or switching
        **selfmute** — Self mute
        **selfdeaf** — Self deafen
        **servermute** — Server mute
        **serverdeaf** — Server deafen
        """
        await handle_group(ctx, types=settings, settings=self.config.guild(ctx.guild).voice, setting_type="voice",
                           slots=self._descriptions["voice"].keys(), descriptions=self._descriptions["voice"])
        await (await self.get_guild_log(ctx.guild)).reload_settings()

    @logset.command(name="info")
    async def logset_info(self, ctx: RedContext):
        """Returns some information on the guild's log settings"""
        guild = await self.get_guild_log(ctx.guild)
        settings = guild.settings

        for channel in settings.get('log_channels', []):
            settings["log_channels"][channel] = ctx.guild.get_channel(settings["log_channels"][channel])
        channels = {x: getattr(settings["log_channels"][x], "mention", None) for x in settings["log_channels"]}

        def description(group: str, item: str):
            return self._descriptions.get(group, {}).get(item, "No description given")

        def build(group: str):
            enabled = [x for x in settings[group] if settings[group][x]] or None
            disabled = [x for x in settings[group] if not settings[group][x]] or None
            strs = [_("**Log channel:** {channel}\n").format(channel=channels.get(group, None))]

            if enabled is not None:
                strs.append("\n".join(_("**{name}**: Enabled — {descriptions}")
                                      .format(name=x, descriptions=description(group, x)) for x in enabled))

            if disabled is not None:
                strs.append("\n".join(_("**{name}**: Disabled — {descriptions}")
                                      .format(name=x, descriptions=description(group, x)) for x in disabled))

            return {"title": _("{group} Settings").format(group=normalize(group)),
                    "content": "\n".join(strs)}

        pages = [
            [build("channels"), build("guild"), build("roles")],
            [build("messages"), build("members"), build("voice")]
        ]

        def convert_page(page: Sequence[dict]) -> str:
            return "\n\n".join(["**\N{HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT} {title}**\n\n{content}"
                               .format(**x) for x in page])

        actions = {
            "close": "\N{CROSS MARK}"
        }

        r, __ = await paginate(ctx=ctx, pages=pages, page_converter=convert_page, actions=actions,
                               title=_("Log Settings"), colour=ctx.me.colour,
                               post_menu_check=lambda x: x != "close")
        try:
            await r.message.clear_reactions()
        except (discord.HTTPException, AttributeError):
            pass

    @logset.command(name="ignored")
    async def info_ignored(self, ctx: RedContext):
        """List all ignored channels in the current guild"""
        ignored_channels = await self.config.all_channels()
        ignored_channels = [x for x in ignored_channels if ignored_channels[x].get("ignored", False) is True]
        ignored_channels = [x.mention for x in [self.bot.get_channel(x) for x in ignored_channels]
                            if x and getattr(x, "guild", None) == ctx.guild]

        if not len(ignored_channels):
            await ctx.send(warning(_("There's no ignored channels in this guild")))

        pages = ["\n".join(x) for x in chunks(ignored_channels, 10)]
        actions = {
            "close": "\N{CROSS MARK}"
        }

        r, __ = await paginate(ctx=ctx, actions=actions, pages=pages,
                               post_menu_check=lambda x: x != "close",
                               title=_("Ignored Channels"), colour=ctx.me.colour)
        try:
            await r.message.clear_reactions()
        except (discord.HTTPException, AttributeError):
            pass

    @logset.group(name="ignore")
    async def logset_ignore(self, ctx: RedContext):
        """Manage ignore settings"""
        await cmd_help(ctx, "ignore")

    @logset_ignore.command(name="guild", aliases=["server"])
    @checks.is_owner()
    async def logset_ignore_guild(self, ctx: RedContext, guild_id: int = None):
        """Ignore the current or specified guild"""
        guild = ctx.guild if not guild_id else self.bot.get_guild(guild_id)
        if not guild:
            await ctx.send(warning(_("I couldn't find that guild")))
            return
        await self.config.guild(guild).ignored.set(True)
        await (await self.get_guild_log(guild)).reload_settings()
        await ctx.send(tick(_("Now ignoring guild **{guild}**").format(guild=escape(guild.name, mass_mentions=True))))

    @logset_ignore.command(name="member")
    async def logset_ignore_member(self, ctx: RedContext, member: discord.Member):
        """Ignore a specified member from logging"""
        await self.config.member(member).ignored.set(True)
        await (await self.get_guild_log(ctx.guild)).reload_settings()
        await ctx.send(tick(_("Now ignoring member **{member}**").format(member=str(member))))

    @logset_ignore.command(name="role")
    async def logset_ignore_role(self, ctx: RedContext, *, role: discord.Role):
        """Ignore a role from logging

        This only ignores the role from role-based logging; any members with the role
        will have to be ignored individually with `[p]logset ignore member`
        """
        await self.config.role(role).ignored.set(True)
        await (await self.get_guild_log(ctx.guild)).reload_settings()
        await ctx.send(tick(_("Now ignoring role **{role}**")
                            .format(role=escape(str(role), mass_mentions=True, formatting=True))))

    @logset_ignore.command(name="channel")
    async def logset_ignore_channel(self, ctx: RedContext,
                                    channel: discord.TextChannel or discord.VoiceChannel = None):
        """Ignore a specified text channel from logging"""
        await self.config.channel(channel or ctx.channel).ignored.set(True)
        await (await self.get_guild_log(ctx.guild)).reload_settings()
        await ctx.send(tick(_("Now ignoring channel {channel}").format(channel=(channel or ctx.channel).mention)))

    @logset_ignore.command(name="category")
    async def logset_ignore_category(self, ctx: RedContext, category: discord.CategoryChannel):
        """Ignore all channels in a category from logging"""
        ignored = []
        for channel in category.channels:
            await self.config.channel(channel).ignored.set(True)
            ignored.append(channel)
        if not ignored:
            await ctx.send(warning(_("Failed to ignore any channels in that category")))
            return
        await (await self.get_guild_log(ctx.guild)).reload_settings()
        _ignored = ["**❯** " + x.mention for x in ignored]
        ignored = "\n".join(_ignored)
        plural = "s" if len(_ignored) != 1 else ""
        await ctx.send(tick(_("Successfully ignored the following channel{plural}:\n\n{channels}")
                            .format(plural=plural, channels=ignored)))

    @logset.group(name="unignore")
    async def logset_unignore(self, ctx: RedContext):
        """Remove a previous ignore"""
        await cmd_help(ctx, "unignore")

    @logset_unignore.command(name="guild", aliases=["server"])
    @checks.is_owner()
    async def logset_unignore_guild(self, ctx: RedContext, guild_id: int = None):
        """Unignore the current or specified guild"""
        guild = ctx.guild if not guild_id else self.bot.get_guild(guild_id)
        if not guild:
            await ctx.send(warning(_("I couldn't find that guild")))
            return
        await self.config.guild(guild).ignored.set(False)
        await (await self.get_guild_log(guild)).reload_settings()
        await ctx.send(tick(_("No longer ignoring guild **{guild}**")
                            .format(guild=escape(guild.name, mass_mentions=True))))

    @logset_unignore.command(name="member")
    async def logset_unignore_member(self, ctx: RedContext, member: discord.Member):
        """Unignore a specified member from logging"""
        await self.config.member(member).ignored.set(False)
        await (await self.get_guild_log(ctx.guild)).reload_settings()
        await ctx.send(tick(_("No longer ignoring member **{member}**").format(member=str(member))))

    @logset_unignore.command(name="role")
    async def logset_unignore_role(self, ctx: RedContext, *, role: discord.Role):
        """Unignore a role from logging"""
        await self.config.role(role).ignored.set(False)
        await (await self.get_guild_log(ctx.guild)).reload_settings()
        await ctx.send(tick(_("No longer ignoring role **{role}**")
                            .format(role=escape(str(role), mass_mentions=True, formatting=True))))

    @logset_unignore.command(name="channel")
    async def logset_unignore_channel(self, ctx: RedContext,
                                      channel: discord.TextChannel or discord.VoiceChannel = None):
        """Unignore a specified text channel from logging"""
        await self.config.channel(channel or ctx.channel).ignored.set(False)
        await (await self.get_guild_log(ctx.guild)).reload_settings()
        await ctx.send(tick(_("No longer ignoring channel {channel}").format(channel=(channel or ctx.channel).mention)))

    @logset_unignore.command(name="category")
    async def logset_unignore_category(self, ctx: RedContext, category: discord.CategoryChannel):
        """Unignore all channels in a category from logging"""
        ignored = []
        for channel in category.channels:
            await self.config.channel(channel).ignored.set(False)
            ignored.append(channel)
        if not ignored:
            await ctx.send(warning(_("Failed to unignore any channels in that category")))
            return
        await (await self.get_guild_log(ctx.guild)).reload_settings()
        _ignored = ["**❯** " + x.mention for x in ignored]
        ignored = "\n".join(_ignored)
        plural = "s" if len(_ignored) != 1 else ""
        await ctx.send(tick(_("No longer ignoring the following channel{plural}:\n\n{channels}")
                            .format(plural=plural, channels=ignored)))

    @logset.command(name="reset")
    async def logset_reset(self, ctx: RedContext):
        """Reset the guild's log settings"""
        if await confirm(ctx, _("Are you sure you want to reset this guild's log settings?"),
                         colour=discord.Colour.red()):
            await self.config.guild(ctx.guild).set(self.config.guild(ctx.guild).defaults)
            await (await self.get_guild_log(ctx.guild)).reload_settings()
            await ctx.send(embed=discord.Embed(description=_("Guild log settings reset."),
                                               colour=discord.Colour.green()))
        else:
            await ctx.send(embed=discord.Embed(description=_("Okay then."), colour=discord.Colour.gold()))

    ###################
    #    Listeners    #
    ###################

    async def on_message_delete(self, message: discord.Message):
        if getattr(message, "guild", None) is None:
            return
        guild = await self.get_guild_log(message.guild)
        await guild.log("messages", LogType.DELETE, deleted=message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if getattr(after, "guild", None) is None:
            return
        guild = await self.get_guild_log(after.guild)
        await guild.log("messages", LogType.UPDATE, before=before, after=after)

    async def on_member_join(self, member: discord.Member):
        guild = await self.get_guild_log(member.guild)
        await guild.log("members", LogType.CREATE, created=member)

    async def on_member_leave(self, member: discord.Member):
        guild = await self.get_guild_log(member.guild)
        await guild.log("members", LogType.DELETE, deleted=member)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = await self.get_guild_log(after.guild)
        await guild.log("members", LogType.UPDATE, before=before, after=after)

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if hasattr(channel, "guild"):
            guild = await self.get_guild_log(channel.guild)
            await guild.log("channels", LogType.CREATE, created=channel)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if hasattr(channel, "guild"):
            guild = await self.get_guild_log(channel.guild)
            await guild.log("channels", LogType.DELETE, deleted=channel)

    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if hasattr(after, "guild"):
            guild = await self.get_guild_log(after.guild)
            await guild.log("channels", LogType.UPDATE, before=before, after=after)

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        if not hasattr(member, "guild"):
            return
        guild = await self.get_guild_log(member.guild)
        await guild.log("voice", LogType.UPDATE, before=before, after=after, member=member)

    async def on_guild_role_create(self, role: discord.Role):
        guild = await self.get_guild_log(role.guild)
        await guild.log("roles", LogType.CREATE, created=role)

    async def on_guild_role_delete(self, role: discord.Role):
        guild = await self.get_guild_log(role.guild)
        await guild.log("roles", LogType.DELETE, deleted=role)

    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        guild = await self.get_guild_log(after.guild)
        await guild.log("roles", LogType.UPDATE, before=before, after=after)

    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        guild = await self.get_guild_log(after)
        await guild.log("server", LogType.UPDATE, before=before, after=after)


async def handle_group(ctx: RedContext, slots: Sequence[str], types: Sequence[str], settings: Group, setting_type: str,
                       descriptions: Dict[str, str] = None):
    if len(types) == 0:
        await ctx.send(embed=status_embed(settings={**{x: False for x in slots}, **await settings()},
                                          title=_("Current {type} Log Settings").format(type=setting_type.title()),
                                          descriptions=descriptions))
        return
    try:
        settings = await group_toggle(group=settings, toggle_keys=types, slots=slots, strict_slots=True)
    except KeyError as e:
        await ctx.send(warning(_("'{}' is not an available setting").format(e)))
        return
    embed = status_embed(settings=settings, title="{} Log Settings".format(setting_type.title()),
                         descriptions=descriptions)
    await ctx.send(tick(_("Updated {type} log settings").format(type=setting_type)), embed=embed)


def add_descriptions(items: List[str], descriptions: Dict[str, str] = None) -> str:
    if descriptions is None:
        descriptions = {}
    for item in items:
        index = items.index(item)
        items[index] = f"**{item}** — {descriptions.get(item, 'No description set')}"
    return "\n".join(items)


def status_embed(settings: Dict[str, bool], title: str, descriptions: Dict[str, str] = None) -> discord.Embed:
    enabled = [x for x in settings if settings[x]] or None
    disabled = [x for x in settings if not settings[x]] or None

    if enabled is not None:
        enabled = add_descriptions(enabled, descriptions)
    else:
        enabled = _("**None** — All of these settings are disabled")

    if disabled is not None:
        disabled = add_descriptions(disabled, descriptions)
    else:
        disabled = _("**None** — All of these settings are enabled")

    arrow = "\N{HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT}"
    embed = discord.Embed(colour=discord.Colour.blurple(), title=title,
                          description=_("**{arrow} Enabled Log Settings**\n{enabled}\n\n"
                                        "**{arrow} Disabled Log Settings**\n{disabled}")
                          .format(arrow=arrow, enabled=enabled, disabled=disabled))
    return embed
