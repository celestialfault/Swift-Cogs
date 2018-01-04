import discord
from collections import namedtuple
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import info, error, box, warning

from logs.utils import toggle, cmd_help, GuildChannel, handle_group
from logs.guildlog import GuildLog, LogType
from logs.types import *

_guilds = {}


# noinspection PyShadowingNames
class Logs:
    """Log anything and everything that happens in your server"""

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
        channel = channel.id if channel else None
        # Half-assed workarounds 101
        channels = self.config.guild(ctx.guild).log_channels.defaults
        for item in channels:
            channels[item] = channel
        await self.config.guild(ctx.guild).log_channels.set(channels)
        await ctx.tick()

    @logset_logchannel.command(name="role")
    async def logchannel_role(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set the role log channel"""
        await self.config.guild(ctx.guild).log_channels.roles.set(channel.id if channel else None)
        await ctx.tick()

    @logset_logchannel.command(name="emoji")
    async def logchannel_emoji(self, ctx: RedContext, channel: discord.TextChannel = None):
        await self.config.guild(ctx.guild).log_channels.emoji.set(channel.id if channel else None)
        await ctx.tick()

    @logset_logchannel.command(name="guild")
    async def logchannel_guild(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set the guild log channel"""
        await self.config.guild(ctx.guild).log_channels.guild.set(channel.id if channel else None)
        await ctx.tick()

    @logset_logchannel.command(name="message")
    async def logchannel_message(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set the message log channel"""
        await self.config.guild(ctx.guild).log_channels.messages.set(channel.id if channel else None)
        await ctx.tick()

    @logset_logchannel.command(name="channel")
    async def logchannel_channel(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set the channel log channel"""
        await self.config.guild(ctx.guild).log_channels.channels.set(channel.id if channel else None)
        await ctx.tick()

    @logset_logchannel.command(name="voice")
    async def logchannel_voice(self, ctx: RedContext, channel: discord.TextChannel = None):
        """Set the voice status log channel"""
        await self.config.guild(ctx.guild).log_channels.voice.set(channel.id if channel else None)
        await ctx.tick()

    @logset.group(name="format")
    async def logset_format(self, ctx: RedContext):
        """Manage the guild's log format"""
        await cmd_help(ctx, "format")

    @logset_format.command(name="embed")
    async def format_embed(self, ctx: RedContext):
        """Set the guild's log format to embeds"""
        await self.config.guild(ctx.guild).format.set("EMBED")
        await ctx.tick()

    @logset_format.command(name="text")
    async def format_text(self, ctx: RedContext):
        """Set the guild's log format to text"""
        await self.config.guild(ctx.guild).format.set("TEXT")
        await ctx.tick()

    @logset.command(name="guild")
    async def logset_guild(self, ctx: RedContext, *types):
        """Set guild update logging

        Available log types:
        2fa, verification, name, owner, afk, region, content_filter

        Example:
        **❯** **!logset guild name owner**
        **❯** Toggles logging of guild name changes and ownership changes
        """
        slots = ["2fa", "verification", "name", "owner", "afk", "region", "content_filter"]
        # noinspection PyTypeChecker
        await handle_group(ctx, slots, types, self.config.guild(ctx.guild).guild, "guild")

    @logset.command(name="channel")
    async def logset_channel_update(self, ctx: RedContext, *types):
        """Manage channel logging

        Available log types:
        create, delete, name, topic, position, category, bitrate, user_limit

        Example:
        **❯** **!logset channel update name topic bitrate**
        **❯** Toggles logging of channel name, bitrate and topic changes
        """
        slots = ["create", "delete", "name", "topic", "position", "category", "bitrate", "user_limit"]
        # noinspection PyTypeChecker
        await handle_group(ctx, slots, types, self.config.guild(ctx.guild).channels, "channel")

    @logset.command(name="message")
    async def logset_message(self, ctx: RedContext, *types):
        """Manage message logging

        Available log types:
        edit, delete

        Example:
        **❯** **!logset message edit**
        **❯** Toggles logging of message edits

        **NOTE:** It's recommended to notify users about the presence of message logging in public servers
        """
        slots = ["edit", "delete"]
        # noinspection PyTypeChecker
        await handle_group(ctx, slots, types, self.config.guild(ctx.guild).messages, "message")

    @logset.command(name="member")
    async def logset_member(self, ctx: RedContext, *types: str):
        """Manage member logging

        Available log types:
        join, leave, name, nickname, roles

        Example:
        **❯** **!logset member update join roles**
        **❯** Toggles logging of member joining and role updates
        """
        slots = ["join", "leave", "name", "nickname", "roles"]
        # noinspection PyTypeChecker
        await handle_group(ctx, slots, types, self.config.guild(ctx.guild).members, "member")

    @logset.command(name="role")
    async def logset_role_update(self, ctx: RedContext, *types):
        """Manage role logging

        Available log types:
        create, delete, name, hoist, mention, position, permissions, colour

        Example:
        **❯** **!logset role update name permissions**
        **❯** Toggles logging of role name and permission changes
        """
        slots = ["create", "delete", "name", "hoist", "mention", "position", "permissions", "colour"]
        # noinspection PyTypeChecker
        await handle_group(ctx, slots, types, self.config.guild(ctx.guild).role, "role")

    @logset.command(name="voice")
    async def logset_voice(self, ctx: RedContext, *types):
        """Manage voice status logging

        Available types:
        channel, selfmute, servermute, selfdeaf, serverdeaf

        Example:
        **❯** !logset voice servermute serverdeaf
        **❯** Toggles logging server mute and deaf status changes
        """
        slots = ["channel", "selfmute", "selfdeaf", "servermute", "serverdeaf"]
        # noinspection PyTypeChecker
        await handle_group(ctx, slots, types, self.config.guild(ctx.guild).voice, "voice")

    @logset.command(name="emoji")
    async def logset_emoji(self, ctx: RedContext):
        """Toggle emoji creation / deletion logging"""
        toggled = await toggle(self.config.guild(ctx.guild).emojis)
        if toggled:
            await ctx.send(info("Now logging emoji creations/deletions"))
        else:
            await ctx.send(info("No longer logging emoji creations/deletions"))

    @logset.group(name="ignore")
    async def logset_ignore(self, ctx: RedContext):
        """Manage ignore settings"""
        await cmd_help(ctx, "ignore")

    @logset_ignore.command(name="guild")
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

    @logset_unignore.command(name="guild")
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
        await self.config.guild(ctx.guild).clear()
        await ctx.tick()

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
    async def fakeleave(self, ctx: RedContext, member: discord.Member = None):
        """Fake a member leave"""
        await self.on_member_leave(member or ctx.author)

    @logset_debug.command(name="fakejoin")
    async def fakejoin(self, ctx: RedContext, member: discord.Member = None):
        """Fake a member join"""
        await self.on_member_join(member or ctx.author)

    @logset_debug.command(name="fakeemoji")
    async def fakeemoji(self, ctx: RedContext, emoji: discord.Emoji, remove: bool=False):
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
    async def fakeedit(self, ctx: RedContext, *, text: str):
        """Fake a message edit with the provided text"""
        FakeMessage = namedtuple("Message", "guild author content channel type")
        after = FakeMessage(author=ctx.author, guild=ctx.guild, channel=ctx.channel, content=text,
                            type=ctx.message.type)
        # noinspection PyTypeChecker
        await self.on_message_edit(ctx.message, after)

    @logset_debug.command()
    async def getchannel(self, ctx: RedContext, *, channel: GuildChannel):
        """Get a channel by name and return it's channel type"""
        await ctx.send(box("{} (type: {})".format(str(channel), type(channel)), lang="python"))

    @logset_debug.command(name="fakedelete")
    async def fakedelete(self, ctx: RedContext):
        """Fake a message deletion"""
        await self.on_message_delete(ctx.message)

    ###################
    #    Listeners    #
    ###################

    async def on_message_delete(self, message: discord.Message):
        if isinstance(message.channel, discord.DMChannel):
            return
        if not await self.config.guild(message.guild).messages.delete():
            return
        await self.get_guild_log(message.guild).log(MessageLogType, LogType.DELETE, deleted=message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if isinstance(after.channel, discord.DMChannel):
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
        guild = channel.guild
        if not await self.config.guild(guild).channels.create():
            return
        await self.get_guild_log(channel.guild).log(ChannelLogType, LogType.CREATE, created=channel)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not await self.config.guild(channel.guild).channels.delete():
            return
        await self.get_guild_log(channel.guild).log(ChannelLogType, LogType.DELETE, deleted=channel)

    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
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
