from collections import namedtuple

import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import info, error, box, warning

from logs.utils import handle_group
from logs.guildlog import GuildLog, LogType
from logs.types import *

from odinair_libs.converters import GuildChannel
from odinair_libs.formatting import tick
from odinair_libs.menus import cmd_help, confirm, ReactMenu
from odinair_libs.config import toggle

_guilds = {}


# noinspection PyShadowingNames
class Logs:
    """Log anything and everything that happens in your server"""
    _descriptions = {
        "guild": {
            "2fa": "Two-factor authentication requirement",
            "verification": "Member verification level",
            "name": "Guild name",
            "owner": "Ownership changes",
            "afk": "AFK channel and timeout",
            "region": "Voice region",
            "content_filter": "Explicit content filter"
        },
        "channels": {
            "create": "Channel creation",
            "delete": "Channel deletion",
            "name": "Channel name",
            "topic": "Text channel topics",
            "category": "Channel category",
            "bitrate": "Voice channel bitrate",
            "user_limit": "Voice channel user limit",
            "position": "Channel position changes (this option can be spammy!)"
        },
        "messages": {
            "edit": "Message edits",
            "delete": "Message deletions"
        },
        "members": {
            "join": "Member joining",
            "leave": "Member leaving",
            "name": "Member username changes",
            "discriminator": "Member discriminator changes",
            "nickname": "Member nickname changes",
            "roles": "Member role changes"
        },
        "roles": {
            "create": "Role creations",
            "delete": "Role deletions",
            "name": "Role name",
            "hoist": "Role hoist status",
            "mention": "Role mentionable status",
            "permissions": "Role permissions",
            "colour": "Role colour",
            "position": "Role position changes (this option can be spammy!)"
        },
        "voice": {
            "channel": "Member voice channel joining, leaving, or switching",
            "selfmute": "Member self-mute",
            "selfdeaf": "Member self-deaf",
            "servermute": "Member server mute",
            "serverdeaf": "Member server deafen"
        }
    }

    def __init__(self, bot: Red, config: Config):
        self.bot = bot
        self.config = config

    @commands.group(name="logset")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def logset(self, ctx: RedContext):
        """Manage guild log settings"""
        if ctx.guild.id not in _guilds:
            _guilds[ctx.guild.id] = GuildLog(ctx.guild)
        await cmd_help(ctx, "")

    @logset.group(name="logchannel")
    async def logset_logchannel(self, ctx: RedContext):
        """Manage the guild's log channels"""
        await cmd_help(ctx, "logchannel")

    @logset_logchannel.command(name="all")
    async def logchannel_all(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set or clear all log channels at once"""
        # Half-assed workarounds 101
        channels = self.config.guild(ctx.guild).log_channels.defaults
        if channel is not None:
            channels = {x: channel.id if channel else None for x in channels}
        await self.config.guild(ctx.guild).log_channels.set(channels)

        if channel is not None:
            await ctx.send(tick("Set all log channels to {}".format(channel.mention)))
        else:
            await ctx.send(tick("Cleared all set log channels"))

    @logset_logchannel.command(name="role")
    async def logchannel_role(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set the role log channel"""
        await self.config.guild(ctx.guild).log_channels.roles.set(channel.id if channel else None)
        if channel is not None:
            await ctx.send(tick("Set the role log channel to {}".format(channel.mention)))
        else:
            await ctx.send(tick("Cleared the set role log channel"))

    @logset_logchannel.command(name="emoji")
    async def logchannel_emoji(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set the emoji log channel"""
        await self.config.guild(ctx.guild).log_channels.emoji.set(channel.id if channel else None)
        if channel is not None:
            await ctx.send(tick("Set the emoji log channel to {}".format(channel.mention)))
        else:
            await ctx.send(tick("Cleared the set emoji log channel"))

    @logset_logchannel.command(name="guild", aliases=["server"])
    async def logchannel_guild(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set the guild log channel"""
        await self.config.guild(ctx.guild).log_channels.guild.set(channel.id if channel else None)
        if channel is not None:
            await ctx.send(tick("Set the guild log channel to {}".format(channel.mention)))
        else:
            await ctx.send(tick("Cleared the set guild log channel"))

    @logset_logchannel.command(name="message")
    async def logchannel_message(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set the message log channel"""
        await self.config.guild(ctx.guild).log_channels.messages.set(channel.id if channel else None)
        if channel is not None:
            await ctx.send(tick("Set the message log channel to {}".format(channel.mention)))
        else:
            await ctx.send(tick("Cleared the set message log channel"))

    @logset_logchannel.command(name="channel")
    async def logchannel_channel(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set the channel log channel"""
        await self.config.guild(ctx.guild).log_channels.channels.set(channel.id if channel else None)
        if channel is not None:
            await ctx.send(tick("Set the channel log channel to {}".format(channel.mention)))
        else:
            await ctx.send(tick("Cleared the set channel log channel"))

    @logset_logchannel.command(name="voice")
    async def logchannel_voice(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set the voice status log channel"""
        await self.config.guild(ctx.guild).log_channels.voice.set(channel.id if channel else None)
        if channel is not None:
            await ctx.send(tick("Set the voice log channel to {}".format(channel.mention)))
        else:
            await ctx.send(tick("Cleared the set voice log channel"))

    @logset.group(name="format")
    async def logset_format(self, ctx: RedContext):
        """Manage the guild's log format"""
        await cmd_help(ctx, "format")

    @logset_format.command(name="embed")
    async def format_embed(self, ctx: RedContext):
        """Set the guild's log format to embeds"""
        await self.config.guild(ctx.guild).format.set("EMBED")
        await ctx.send(tick("Log messages will now be embeds"))

    @logset_format.command(name="text")
    async def format_text(self, ctx: RedContext):
        """Set the guild's log format to text"""
        await self.config.guild(ctx.guild).format.set("TEXT")
        await ctx.send(tick("Log messages will now be plain text"))

    @logset.group(name="check")
    async def logset_check(self, ctx: RedContext):
        """Change the check type for changes

        This setting is most visible with voice status updates and voice channel ignores"""
        await cmd_help(ctx, "check")

    @logset_check.command(name="both")
    async def logset_both(self, ctx: RedContext):
        """Set logging to check both before and after values to determine ignore status"""
        await self.config.guild(ctx.guild).check_type.set("both")
        await ctx.send(tick("Log ignoring will now check the unchanged values in updates"))

    @logset_check.command(name="after")
    async def logset_after(self, ctx: RedContext):
        """Set logging to check the after values to determine ignore status"""
        await self.config.guild(ctx.guild).check_type.set("after")
        await ctx.send(tick("Log ignoring will now check the changed values in updates"))

    @logset_check.command(name="before")
    async def logset_before(self, ctx: RedContext):
        """Set logging to check the before values to determine ignore status"""
        await self.config.guild(ctx.guild).check_type.set("before")
        await ctx.send(tick("Log ignoring will now check the both the unchanged and changed values in updates"))

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

        **NOTE:** It's recommended to notify users about the presence of message logging in public servers
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

    @logset.command(name="emoji")
    async def logset_emoji(self, ctx: RedContext):
        """Toggle emoji creation / deletion logging"""
        toggled = await toggle(self.config.guild(ctx.guild).emojis)
        if toggled:
            await ctx.send(info("Now logging emoji creations/deletions"))
        else:
            await ctx.send(info("No longer logging emoji creations/deletions"))

    @logset.group(name="info", invoke_without_command=True)
    async def logset_info(self, ctx: RedContext):
        """Returns some information on the guild's log settings"""
        settings = await self.config.guild(ctx.guild)()

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
            [
                build("channels"),
                build("guild"),
                build("roles")
            ],
            [
                build("messages"),
                build("members"),
                build("voice")
            ],
            [
                {"title": "Emoji Updates", "content": "**Log channel:** {}\n\n**Enabled:** {}".format(
                    channels.get("emoji", None), str(settings.get("emojis", False)))},
                {
                    "title": "Log Settings",
                    "content": "**Check type:** {type}\n"
                               "**Log format:** {format}"
                               "".format(
                                         type=str(settings.get("check_type", "after")).title(),
                                         format=str(settings.get("format", "EMBED")).title())
                }
            ]
        ]

        actions = {
            "prev": "\N{BLACK LEFT-POINTING TRIANGLE}",
            "close": "\N{CROSS MARK}",
            "next": "\N{BLACK RIGHT-POINTING TRIANGLE}"
        }
        curr_page = 0

        embed = discord.Embed(colour=discord.Colour.blurple(), title="Log Settings")
        for item in pages[curr_page]:
            embed.add_field(name=item["title"], value=item["content"], inline=False)
        embed.set_footer(text="Page {}/{}".format(curr_page + 1, len(pages)))
        menu = ReactMenu(ctx, actions, embed=embed, timeout=60.0,
                         post_action_check=lambda action: action != "close")
        result = None

        while True:
            embed = discord.Embed(colour=discord.Colour.blurple(), title="Log Settings")
            for item in pages[curr_page]:
                embed.add_field(name=item["title"], value=item["content"], inline=False)
            embed.set_footer(text="Page {}/{}".format(curr_page + 1, len(pages)))
            if result is not None:
                await menu.message.edit(embed=embed)
            result = await menu.prompt()
            if result.action == "close" or result.timed_out is True:
                try:
                    await menu.message.clear_reactions()
                except discord.Forbidden:
                    pass
                break
            elif result.action == "next":
                if curr_page + 1 > len(pages) - 1:
                    continue
                curr_page += 1
            elif result.action == "prev":
                if curr_page - 1 < 0:
                    continue
                curr_page -= 1

    @logset_info.command(name="ignored")
    async def info_ignored(self, ctx: RedContext):
        ignored_channels = await self.config.all_channels()
        ignored_channels = [x for x in ignored_channels if ignored_channels[x].get("ignored", False) is True]
        ignored_channels = [x.mention for x in map(lambda x: self.bot.get_channel(x), ignored_channels) if x]

        if not len(ignored_channels):
            await ctx.send(warning("There's no ignored channels in this guild"))

        pages = []
        items = []
        for item in ignored_channels:
            items.append(item)
            if len(items) == 10:
                pages.append("\n".join(items))
                items = []
        if items:
            pages.append("\n".join(items))

        if len(pages) == 1:
            embed = discord.Embed(colour=discord.Colour.blurple(), title="Ignored Channels", description=pages[0])
            embed.set_footer(text="Page 1/1")
            await ctx.send(embed=embed)
            return

        actions = {
            "prev": "\N{BLACK LEFT-POINTING TRIANGLE}",
            "close": "\N{CROSS MARK}",
            "next": "\N{BLACK RIGHT-POINTING TRIANGLE}"
        }
        curr_page = 0

        embed = discord.Embed(colour=discord.Colour.blurple(), title="Ignored Channels",
                              description=pages[curr_page])
        embed.set_footer(text="Page {}/{}".format(curr_page + 1, len(pages)))
        menu = ReactMenu(ctx, actions, embed=embed, timeout=60.0,
                         post_action_check=lambda action: action != "close")
        result = None

        while True:
            embed = discord.Embed(colour=discord.Colour.blurple(), title="Ignored Channels",
                                  description=pages[curr_page])
            embed.set_footer(text="Page {}/{}".format(curr_page + 1, len(pages)))
            if result is not None:
                await menu.message.edit(embed=embed)
            result = await menu.prompt()
            if result.action == "close" or result.timed_out is True:
                try:
                    await menu.message.clear_reactions()
                except discord.Forbidden:
                    pass
                break
            elif result.action == "next":
                if curr_page + 1 > len(pages) - 1:
                    continue
                curr_page += 1
            elif result.action == "prev":
                if curr_page - 1 < 0:
                    continue
                curr_page -= 1

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
            await ctx.send(error("I couldn't find that guild"))
            return
        await self.config.guild(guild).ignored.set(True)
        await ctx.send("Now ignoring guild **{}**".format(guild.name))

    @logset_ignore.command(name="member")
    async def logset_ignore_member(self, ctx: RedContext, member: discord.Member):
        """Ignore a specified member from logging"""
        await self.config.member(member).ignored.set(True)
        await ctx.send("Now ignoring member **{}**".format(str(member)))

    @logset_ignore.command(name="channel")
    async def logset_ignore_channel(self, ctx: RedContext, channel: GuildChannel = None):
        """Ignore a specified text channel from logging"""
        if channel is not None and isinstance(channel, discord.CategoryChannel):
            await ctx.send(warning("Use `{}logset ignore category` to ignore categories").format(ctx.prefix))
            return
        await self.config.channel(channel or ctx.channel).ignored.set(True)
        await ctx.send("Now ignoring channel {}".format((channel or ctx.channel).mention))

    @logset_ignore.command(name="category")
    async def logset_ignore_category(self, ctx: RedContext, category: discord.CategoryChannel):
        """Ignore all channels in a category from logging"""
        ignored = []
        for channel in category.channels:
            await self.config.channel(channel).ignored.set(True)
            ignored.append(channel)
        if not ignored:
            await ctx.send(error("Failed to ignore any channels in that category"))
            return
        _ignored = ["**❯** " + x.mention for x in ignored]
        ignored = "\n".join(_ignored)
        await ctx.send(info("Successfully ignored the following channel{}:\n\n{}").format(
            "s" if len(_ignored) > 1 else "", ignored))

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
            await ctx.send(error("I couldn't find that guild"))
            return
        await self.config.guild(guild).ignored.set(False)
        await ctx.send("No longer ignoring guild **{}**".format(guild.name))

    @logset_unignore.command(name="member")
    async def logset_unignore_member(self, ctx: RedContext, member: discord.Member):
        """Unignore a specified member from logging"""
        await self.config.member(member).ignored.set(False)
        await ctx.send("No longer ignoring member **{}**".format(str(member)))

    @logset_unignore.command(name="channel")
    async def logset_unignore_channel(self, ctx: RedContext, channel: GuildChannel = None):
        """Unignore a specified text channel from logging"""
        if channel is not None and isinstance(channel, discord.CategoryChannel):
            await ctx.send(warning("Use `{}logset unignore category` to unignore categories").format(ctx.prefix))
            return
        await self.config.channel(channel or ctx.channel).ignored.set(False)
        await ctx.send("No longer ignoring channel {}".format((channel or ctx.channel).mention))

    @logset_unignore.command(name="category")
    async def logset_unignore_category(self, ctx: RedContext, category: discord.CategoryChannel):
        """Unignore all channels in a category from logging"""
        ignored = []
        for channel in category.channels:
            await self.config.channel(channel).ignored.set(False)
            ignored.append(channel)
        if not ignored:
            await ctx.send(error("Failed to unignore any channels in that category\n\n"
                                 "(I'm only able to ignore text channels)"))
            return
        _ignored = ["**❯** " + x.mention for x in ignored]
        ignored = "\n".join(_ignored)
        await ctx.send(info("No longer ignoring the following channel{}:\n\n{}").format(
            "s" if len(_ignored) > 1 else "", ignored))

    @logset.command(name="reset")
    async def logset_reset(self, ctx: RedContext):
        """Reset the guild's log settings"""
        if await confirm(ctx, "Are you sure you want to reset this guild's log settings?", colour=discord.Colour.red()):
            await self.config.guild(ctx.guild).set(self.config.guild(ctx.guild).defaults)
            await ctx.send(embed=discord.Embed(description="Guild log settings reset.", colour=discord.Colour.green()))
        else:
            await ctx.send(embed=discord.Embed(description="Okay then.", colour=discord.Colour.gold()))

    @staticmethod
    def get_guild_log(guild: discord.Guild) -> GuildLog:
        if guild.id not in _guilds:
            _guilds[guild.id] = GuildLog(guild)
        return _guilds[guild.id]

    ####################
    #  Debug Commands  #
    ####################

    @logset.group(name="debug", hidden=True)
    @checks.is_owner()
    async def logset_debug(self, ctx: RedContext):
        """Debug utilities"""
        await cmd_help(ctx, "debug")

    @logset_debug.command(name="fakeleave")
    async def debug_fakeleave(self, ctx: RedContext, member: discord.Member = None):
        """Fake a member leave"""
        await self.on_member_leave(member or ctx.author)

    @logset_debug.command(name="fakejoin")
    async def debug_fakejoin(self, ctx: RedContext, member: discord.Member = None):
        """Fake a member join"""
        await self.on_member_join(member or ctx.author)

    @logset_debug.command(name="fakeemoji")
    async def debug_fakeemoji(self, ctx: RedContext, emoji: discord.Emoji, remove: bool=False):
        """Fake an emoji addition/removal"""
        if emoji.guild != ctx.guild:
            await ctx.send("That emoji isn't in the current guild")
            return
        guild = ctx.guild
        after = guild.emojis
        if remove:
            before = guild.emojis
            after = [x for x in guild.emojis if x != emoji]
        else:
            before = [x for x in guild.emojis if x != emoji]
        await self.on_guild_emojis_update(guild, before, after)

    @logset_debug.command(name="fakeedit")
    async def debug_fakeedit(self, ctx: RedContext, *, text: str):
        """Fake a message edit with the provided text"""
        FakeMessage = namedtuple("Message", "guild author content channel type")
        after = FakeMessage(author=ctx.author, guild=ctx.guild, channel=ctx.channel, content=text,
                            type=ctx.message.type)
        # noinspection PyTypeChecker
        await self.on_message_edit(ctx.message, after)

    @logset_debug.command(name="getchannel")
    async def debug_getchannel(self, ctx: RedContext, *, channel: GuildChannel):
        """Get a channel by name and return it's channel type"""
        await ctx.send(box("{} (type: {})".format(str(channel), type(channel)), lang="python"))

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
        if not await self.config.guild(message.guild).messages.delete():
            return
        await self.get_guild_log(message.guild).log(MessageLogType, LogType.DELETE, deleted=message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if isinstance(after.channel, discord.abc.PrivateChannel):
            return
        if not await self.config.guild(after.guild).messages.edit():
            return
        await self.get_guild_log(after.guild).log(MessageLogType, LogType.UPDATE, before=before, after=after)

    async def on_member_join(self, member: discord.Member):
        if not await self.config.guild(member.guild).members.join():
            return
        await self.get_guild_log(member.guild).log(MemberLogType, LogType.CREATE, created=member)

    async def on_member_leave(self, member: discord.Member):
        if not await self.config.guild(member.guild).members.leave():
            return
        await self.get_guild_log(member.guild).log(MemberLogType, LogType.DELETE, deleted=member)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        await self.get_guild_log(after.guild).log(MemberLogType, LogType.UPDATE, before=before, after=after)

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        guild = channel.guild
        if not await self.config.guild(guild).channels.create():
            return
        # noinspection PyUnresolvedReferences
        await self.get_guild_log(channel.guild).log(ChannelLogType, LogType.CREATE, created=channel)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        if not await self.config.guild(channel.guild).channels.delete():
            return
        # noinspection PyUnresolvedReferences
        await self.get_guild_log(channel.guild).log(ChannelLogType, LogType.DELETE, deleted=channel)

    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        await self.get_guild_log(after.guild).log(ChannelLogType, LogType.UPDATE, before=before, after=after)

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        await self.get_guild_log(member.guild).log(VoiceLogType, LogType.UPDATE, before=before, after=after,
                                                   member=member)

    async def on_guild_role_create(self, role: discord.Role):
        if not await self.config.guild(role.guild).roles.create():
            return
        await self.get_guild_log(role.guild).log(RoleLogType, LogType.CREATE, created=role)

    async def on_guild_role_delete(self, role: discord.Role):
        if not await self.config.guild(role.guild).roles.delete():
            return
        await self.get_guild_log(role.guild).log(RoleLogType, LogType.DELETE, deleted=role)

    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        await self.get_guild_log(after.guild).log(RoleLogType, LogType.UPDATE, before=before, after=after)

    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        await self.get_guild_log(after).log(GuildLogType, LogType.UPDATE, before=before, after=after)

    async def on_guild_emojis_update(self, guild: discord.Guild, before, after):
        if not await self.config.guild(guild).emojis():
            return
        await self.get_guild_log(guild).log(EmojiLogType, LogType.UPDATE, guild=guild, before=before, after=after)
