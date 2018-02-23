from typing import Sequence
from copy import deepcopy

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import box, warning, escape

from logs.utils import handle_group
from logs.guildlog import GuildLog, LogType
from logs import types

from odinair_libs.converters import GuildChannel, chunks
from odinair_libs.formatting import tick
from odinair_libs.menus import cmd_help, confirm, paginate

_guilds = {}
_defaults_guild = {
    "log_channels": {
        "roles": None,
        "guild": None,
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
    "guild": {
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
    "ignored": False,
    "check_type": "after"
}


class Logs:
    """Log anything and everything that happens in your server"""
    _descriptions = {x.name: x.descriptions for x in types.iterable}

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=35908345472, force_registration=True)
        self.config.register_guild(**_defaults_guild)
        self.config.register_member(ignored=False)
        self.config.register_channel(ignored=False)

    async def get_guild_log(self, guild: discord.Guild) -> GuildLog:
        if guild.id not in _guilds:
            guild_ = GuildLog(guild, bot=self.bot, config=self.config)
            await guild_.init()
            _guilds[guild.id] = guild_
        return _guilds[guild.id]

    @commands.group(name="logset")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def logset(self, ctx: RedContext):
        """Manage guild log settings"""
        await self.get_guild_log(ctx.guild)  # the return value is intentionally ignored here
        await cmd_help(ctx, "")

    @logset.group(name="logchannel", invoke_without_command=True)
    async def logset_logchannel(self, ctx: RedContext, channel: discord.TextChannel, *log_types: str):
        """Manage the guild's log channels

        Available log types:

        **guild**, **members**, **roles**, **messages**, **channels**, **voice**

        `all` is also accepted to set all of the above log types at once
        """
        if not log_types:
            await ctx.send_help()
            return
        guild = await self.get_guild_log(ctx.guild)
        if any([x for x in log_types if x.lower() not in guild.config.log_channels.defaults])\
                and "all" not in log_types:
            await ctx.send_help()
            return
        async with guild.config.log_channels() as channels:
            if "all" in log_types:
                defaults = guild.config.log_channels.defaults
                channels.update({x: channel.id for x in defaults})
                await ctx.send(tick(f"Set all log channels to {channel.mention}"))
            else:
                formatted_types = ", ".join([f"**{x.title()}**" for x in log_types])
                await ctx.send(tick(f"Set log channels for types {formatted_types} to {channel.mention}"))
        await guild.reload_settings()

    @logset_logchannel.command(name="clear")
    async def logchannel_clear(self, ctx: RedContext, *log_types: str):
        """Clear log channels for specific types or all log types

        If no log types are passed, all log channels are cleared
        """
        guild = await self.get_guild_log(ctx.guild)
        if any([x for x in log_types if x.lower() not in guild.config.log_channels.defaults]):
            await ctx.send_help()
            return
        if not log_types:
            if not await confirm(ctx, message="Are you sure you want to clear all log channels?"):
                await ctx.send_help()
                return
        async with guild.config.log_channels() as channels:
            if not log_types:
                channels.update(guild.config.log_channels.defaults)
                await ctx.send(tick("Cleared all log channels"))
            else:
                channels.update({x: None for x in log_types})
                formatted_types = ", ".join([f"**{x.title()}**" for x in log_types])
                await ctx.send(tick(f"Cleared log channels for log types {formatted_types}"))
        await guild.reload_settings()

    @logset.command(name="updatecheck")
    async def logset_check(self, ctx: RedContext, check_type: str):
        """Change the check type for log ignoring in update events

        This setting is most visible with voice status updates and voice channel ignores

        Available check types:

        **before** — Check the unchanged values
        **after** — Check the changed values
        **both** — Check *both* changed and unchanged values
        """
        check_type = check_type.lower()
        if check_type not in ('before', 'after', 'both'):
            await ctx.send_help()
            return
        await self.config.guild(ctx.guild).check_type.set(check_type)
        await ctx.send(tick(f"Log ignore checking changed to `{check_type}`"))

    @logset.command(name="guild", aliases=["server"])
    async def logset_guild(self, ctx: RedContext, *settings):
        """Set guild update logging

        Available log settings:

        **2fa** — Guild two factor authentication requirement
        **verification** — Guild verification level
        **name** — Guild name
        **owner** — Guild ownership
        **afk** — Guild AFK channel and timeout
        **region** — Guild voice region
        **content_filter** — Guild NSFW content filter

        Example:
        **❯** `[p]logset guild name owner`
        """
        await handle_group(ctx, types=settings, settings=self.config.guild(ctx.guild).guild, setting_type="guild",
                           slots=["2fa", "verification", "name", "owner", "afk", "region", "content_filter"],
                           descriptions=self._descriptions["guild"])

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

        Example:
        **❯** `[p]logset channel update name topic bitrate`
        """
        await handle_group(ctx, types=settings, settings=self.config.guild(ctx.guild).channels, setting_type="channel",
                           slots=["create", "delete", "name", "topic", "position", "category", "bitrate", "user_limit"],
                           descriptions=self._descriptions["channels"])

    @logset.command(name="message")
    async def logset_message(self, ctx: RedContext, *settings):
        """Manage message logging

        Available log settings:

        **edit** — Message edits
        **delete** — Message deletion

        Example:
        **❯** `[p]logset message edit`
        """
        await handle_group(ctx, types=settings, settings=self.config.guild(ctx.guild).messages, setting_type="message",
                           slots=["edit", "delete"], descriptions=self._descriptions["messages"])

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

        Example:
        **❯** `[p]logset member update discriminator join roles`
        """
        await handle_group(ctx, types=settings, settings=self.config.guild(ctx.guild).members, setting_type="member",
                           slots=["join", "leave", "name", "discriminator", "nickname", "roles"],
                           descriptions=self._descriptions["members"])

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

        Example:
        **❯** `[p]logset role update name permissions`
        """
        await handle_group(ctx, types=settings, settings=self.config.guild(ctx.guild).roles, setting_type="role",
                           slots=["create", "delete", "name", "hoist", "mention", "position", "permissions", "colour"],
                           descriptions=self._descriptions["roles"])

    @logset.command(name="voice")
    async def logset_voice(self, ctx: RedContext, *settings):
        """Manage voice status logging

        Available log settings:

        **channel** — Member voice channel joining, leaving or switching
        **selfmute** — Self mute
        **selfdeaf** — Self deafen
        **servermute** — Server mute
        **serverdeaf** — Server deafen

        Example:
        **❯** `[p]logset voice servermute serverdeaf`
        """
        await handle_group(ctx, types=settings, settings=self.config.guild(ctx.guild).voice, setting_type="voice",
                           slots=["channel", "selfmute", "selfdeaf", "servermute", "serverdeaf"],
                           descriptions=self._descriptions["voice"])

    @logset.command(name="info")
    async def logset_info(self, ctx: RedContext):
        """Returns some information on the guild's log settings"""
        settings = await self.config.guild(ctx.guild).all()

        for channel in settings.get('log_channels', []):
            settings["log_channels"][channel] = ctx.guild.get_channel(settings["log_channels"][channel])
        channels = {x: getattr(settings["log_channels"][x], "mention", None) for x in settings["log_channels"]}

        def build(group: str):
            enabled = [x for x in settings[group] if settings[group][x]] or None
            disabled = [x for x in settings[group] if not settings[group][x]] or None
            strs = ["**Log channel:** {}\n".format(channels.get(group, None))]

            if enabled is not None:
                strs.append("\n".join("**{}**: Enabled — {}"
                                      .format(x, self._descriptions[group].get(x, "No description provided"))
                                      for x in enabled))

            if disabled is not None:
                strs.append("\n".join("**{}**: Disabled — {}"
                                      .format(x, self._descriptions[group].get(x, "No description provided"))
                                      for x in disabled))

            return {"title": "{} Settings".format(group.replace("_", " ").title()),
                    "content": "\n".join(strs)}

        pages = [
            [build("channels"), build("guild"), build("roles")],
            [build("messages"), build("members"), build("voice")],
            [
                {
                    "title": "Emoji Updates",
                    "content": "**Log channel:** {channel}\n\n"
                               "**Enabled:** {enabled}"
                               "".format(channel=channels.get("emoji", None),
                                         enabled=str(settings.get("emojis", False)))
                },
                {
                    "title": "Log Settings",
                    "content": "**Check type:** {type}\n"
                               "**Log format:** {format}"
                               "".format(type=str(settings.get("check_type", "after")).title(),
                                         format=str(settings.get("format", "EMBED")).title())
                }
            ]
        ]

        def convert_page(page: Sequence[dict]) -> str:
            return "\n\n".join(["**\N{HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT} {title}**\n\n{content}"
                                .format(**x) for x in page])

        actions = {
            "close": "\N{CROSS MARK}"
        }

        r, _ = await paginate(ctx=ctx, pages=pages, page_converter=convert_page, actions=actions,
                              title="Log Settings", colour=ctx.me.colour,
                              post_menu_check=lambda x: x != "close")
        try:
            if not r.timed_out:
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
            await ctx.send(warning("There's no ignored channels in this guild"))

        pages = ["\n".join(x) for x in chunks(ignored_channels, 10)]
        actions = {
            "close": "\N{CROSS MARK}"
        }

        r, _ = await paginate(ctx=ctx, actions=actions, pages=pages,
                              post_menu_check=lambda x: x != "close",
                              title="Ignored Channels", colour=ctx.me.colour)
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
            await ctx.send(warning("I couldn't find that guild"))
            return
        await self.config.guild(guild).ignored.set(True)
        await ctx.send(tick(f"Now ignoring guild **{escape(guild.name, mass_mentions=True)}**"))

    @logset_ignore.command(name="member")
    async def logset_ignore_member(self, ctx: RedContext, member: discord.Member):
        """Ignore a specified member from logging"""
        await self.config.member(member).ignored.set(True)
        await ctx.send(tick(f"Now ignoring member **{member!s}**"))

    @logset_ignore.command(name="channel")
    async def logset_ignore_channel(self, ctx: RedContext, channel: GuildChannel = None):
        """Ignore a specified text channel from logging"""
        if channel is not None and isinstance(channel, discord.CategoryChannel):
            await ctx.send(warning("Use `{}logset ignore category` to ignore categories").format(ctx.prefix))
            return
        await self.config.channel(channel or ctx.channel).ignored.set(True)
        await ctx.send(tick(f"Now ignoring channel {(channel or ctx.channel).mention}"))

    @logset_ignore.command(name="category")
    async def logset_ignore_category(self, ctx: RedContext, category: discord.CategoryChannel):
        """Ignore all channels in a category from logging"""
        ignored = []
        for channel in category.channels:
            await self.config.channel(channel).ignored.set(True)
            ignored.append(channel)
        if not ignored:
            await ctx.send(warning("Failed to ignore any channels in that category"))
            return
        _ignored = ["**❯** " + x.mention for x in ignored]
        ignored = "\n".join(_ignored)
        plural = "s" if len(_ignored) != 1 else ""
        await ctx.send(tick(f"Successfully ignored the following channel{plural}:\n\n{ignored}"))

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
            await ctx.send(warning("I couldn't find that guild"))
            return
        await self.config.guild(guild).ignored.set(False)
        await ctx.send(tick(f"No longer ignoring guild **{escape(guild.name, mass_mentions=True)}**"))

    @logset_unignore.command(name="member")
    async def logset_unignore_member(self, ctx: RedContext, member: discord.Member):
        """Unignore a specified member from logging"""
        await self.config.member(member).ignored.set(False)
        await ctx.send(tick(f"No longer ignoring member **{member!s}**"))

    @logset_unignore.command(name="channel")
    async def logset_unignore_channel(self, ctx: RedContext, channel: GuildChannel = None):
        """Unignore a specified text channel from logging"""
        if channel is not None and isinstance(channel, discord.CategoryChannel):
            await ctx.send(warning("Use `{}logset unignore category` to unignore categories").format(ctx.prefix))
            return
        await self.config.channel(channel or ctx.channel).ignored.set(False)
        await ctx.send(tick(f"No longer ignoring channel {(channel or ctx.channel).mention}"))

    @logset_unignore.command(name="category")
    async def logset_unignore_category(self, ctx: RedContext, category: discord.CategoryChannel):
        """Unignore all channels in a category from logging"""
        ignored = []
        for channel in category.channels:
            await self.config.channel(channel).ignored.set(False)
            ignored.append(channel)
        if not ignored:
            await ctx.send(warning("Failed to unignore any channels in that category"))
            return
        _ignored = ["**❯** " + x.mention for x in ignored]
        ignored = "\n".join(_ignored)
        plural = "s" if len(_ignored) != 1 else ""
        await ctx.send(tick(f"No longer ignoring the following channel{plural}:\n\n{ignored}"))

    @logset.command(name="reset")
    async def logset_reset(self, ctx: RedContext):
        """Reset the guild's log settings"""
        if await confirm(ctx, "Are you sure you want to reset this guild's log settings?", colour=discord.Colour.red()):
            await self.config.guild(ctx.guild).set(self.config.guild(ctx.guild).defaults)
            await ctx.send(embed=discord.Embed(description="Guild log settings reset.", colour=discord.Colour.green()))
        else:
            await ctx.send(embed=discord.Embed(description="Okay then.", colour=discord.Colour.gold()))

    ####################
    #  Debug Commands  #
    ####################

    @logset.group(name="debug", hidden=True)
    @checks.is_owner()
    async def logset_debug(self, ctx: RedContext):
        """Debug utilities"""
        await cmd_help(ctx, "debug")

    @logset_debug.command(name="fakejoin")
    async def debug_fakejoin(self, ctx: RedContext, member: discord.Member = None):
        """Fake a member join"""
        await self.on_member_join(member or ctx.author)

    @logset_debug.command(name="fakeleave")
    async def debug_fakeleave(self, ctx: RedContext, member: discord.Member = None):
        """Fake a member leave"""
        await self.on_member_leave(member or ctx.author)

    @logset_debug.command(name="fakeedit")
    async def debug_fakeedit(self, ctx: RedContext, *, text: str):
        """Fake a message edit with the provided text"""
        after = deepcopy(ctx.message)
        after.content = text
        await self.on_message_edit(ctx.message, after)

    @logset_debug.command(name="getchannel")
    async def debug_getchannel(self, ctx: RedContext, *, channel: GuildChannel):
        """Get a channel by name and return it's channel type"""
        await ctx.send(box(f"{channel!r}"))

    @logset_debug.command(name="fakedelete")
    async def debug_fakedelete(self, ctx: RedContext):
        """Fake a message deletion"""
        await self.on_message_delete(ctx.message)

    ###################
    #    Listeners    #
    ###################

    async def on_message_delete(self, message: discord.Message):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return
        guild = await self.get_guild_log(message.guild)
        await guild.log("messages", LogType.DELETE, deleted=message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if isinstance(after.channel, discord.abc.PrivateChannel):
            return
        guild = await self.get_guild_log(after.guild)
        await guild.log("messages", LogType.UPDATE, before=before, after=after)

    async def on_member_join(self, member: discord.Member):
        guild = await self.get_guild_log(member.guild)
        await guild.log("member", LogType.CREATE, created=member)

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
        await guild.log("guild", LogType.UPDATE, before=before, after=after)
