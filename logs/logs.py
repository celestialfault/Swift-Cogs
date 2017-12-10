import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config
from redbot.core.utils.chat_formatting import info

from .utils import toggle, get_formatter, set_formatter, cmd_help, group_set


class Logs:
    def __init__(self, bot: Red, config: Config):
        self.bot = bot
        self.config = config

    @commands.group(name="logset")
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def logset(self, ctx: RedContext):
        """Manage guild log settings"""
        await cmd_help(ctx, "")

    @logset.group(name="logchannel")
    async def logset_logchannel(self, ctx: RedContext):
        """Manage the guild's log channels"""
        await cmd_help(ctx, "logchannel")

    @logset_logchannel.command(name="all")
    async def logchannel_all(self, ctx: RedContext, channel: discord.TextChannel=None):
        """Set or clear all log channels at once"""
        channel = channel.id if channel else None
        # Half-assed workarounds 101
        channels = self.config.guild(ctx.guild).log_channels.defaults
        for item in channels:
            channels[item] = channel
        await self.config.guild(ctx.guild).log_channels.set(channels)
        await ctx.tick()

    @logset_logchannel.command(name="role")
    async def logchannel_role(self, ctx: RedContext, channel: discord.TextChannel=None):
        """Set the role log channel"""
        await self.config.guild(ctx.guild).log_channels.roles.set(channel.id if channel else None)
        await ctx.tick()

    @logset_logchannel.command(name="guild")
    async def logchannel_guild(self, ctx: RedContext, channel: discord.TextChannel=None):
        """Set the guild log channel"""
        await self.config.guild(ctx.guild).log_channels.guild.set(channel.id if channel else None)
        await ctx.tick()

    @logset_logchannel.command(name="message")
    async def logchannel_message(self, ctx: RedContext, channel: discord.TextChannel=None):
        """Set the message log channel"""
        await self.config.guild(ctx.guild).log_channels.messages.set(channel.id if channel else None)
        await ctx.tick()

    @logset_logchannel.command(name="channel")
    async def logchannel_channel(self, ctx: RedContext, channel: discord.TextChannel=None):
        """Set the channel log channel"""
        await self.config.guild(ctx.guild).log_channels.channels.set(channel.id if channel else None)
        await ctx.tick()

    @logset_logchannel.command(name="voice")
    async def logchannel_voice(self, ctx: RedContext, channel: discord.TextChannel=None):
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
        await set_formatter("EMBED", self.config.guild(ctx.guild).format, ctx.guild)
        await ctx.tick()

    @logset_format.command(name="text")
    async def format_text(self, ctx: RedContext):
        """Set the guild's log format to text"""
        await set_formatter("TEXT", self.config.guild(ctx.guild).format, ctx.guild)
        await ctx.tick()

    @logset.command(name="guild")
    async def logset_guild(self, ctx: RedContext, *types):
        """Set guild update logging

        Available log types:
        2fa, verification, name, owner, afk

        Example:
            !logset guild name owner
        -> Logs guild name and owner changes, but not AFK, verification level or 2FA requirement changes"""
        _set = await group_set(types, self.config.guild(ctx.guild).guild)
        msg = "{}\n{}".format(info("Updated guild update log settings"), _set)
        await ctx.send(msg)

    @logset.group(name="channel")
    async def logset_channel(self, ctx: RedContext):
        """Manage channel logging"""
        await cmd_help(ctx, "channel")

    @logset_channel.command(name="create")
    async def logset_channel_create(self, ctx: RedContext):
        """Toggle logging of channel creation"""
        toggled = toggle(self.config.guild(ctx.guild).channels.create)
        if toggled:
            await ctx.send(info("Now logging channel creation"))
        else:
            await ctx.send(info("No longer logging channel creation"))

    @logset_channel.command(name="delete")
    async def logset_channel_delete(self, ctx: RedContext):
        """Toggle logging of channel deletion"""
        toggled = toggle(self.config.guild(ctx.guild).channels.delete)
        if toggled:
            await ctx.send(info("Now logging channel deletion"))
        else:
            await ctx.send(info("No longer logging channel deletion"))

    @logset_channel.command(name="update")
    async def logset_channel_update(self, ctx: RedContext, *types):
        """Set channel update logging

        Available log types:
        name, topic, position, category, bitrate, user_limit

        Example:
            !logset channel update name topic bitrate
        -> Logs channel name, bitrate and topic changes, but not position, user limit, or parent category changes"""
        _set = await group_set(types, self.config.guild(ctx.guild).channels.update)
        msg = "{}\n{}".format(info("Updated channel update log settings"), _set)
        await ctx.send(msg)

    @logset.command(name="message")
    async def logset_message(self, ctx: RedContext, *types):
        """Set message logging

        Available log types:
        edit, delete

        Example:
            !logset message delete
        -> Logs message deletion, but not message edits"""
        _set = await group_set(types, self.config.guild(ctx.guild).messages)
        msg = "{}\n{}".format(info("Updated message log settings"), _set)
        await ctx.send(msg)

    @logset.group(name="member")
    async def logset_member(self, ctx: RedContext):
        """Manage member logging"""
        await cmd_help(ctx, "member")

    @logset_member.command(name="join")
    async def logset_member_join(self, ctx: RedContext):
        """Toggle logging of member joins"""
        toggled = toggle(self.config.guild(ctx.guild).members.join)
        if toggled:
            await ctx.send(info("Now logging member joins"))
        else:
            await ctx.send(info("No longer logging member joins"))

    @logset_member.command(name="leave")
    async def logset_member_leave(self, ctx: RedContext):
        """Toggle logging of member leaving"""
        toggled = toggle(self.config.guild(ctx.guild).members.leave)
        if toggled:
            await ctx.send(info("Now logging member leaving"))
        else:
            await ctx.send(info("No longer logging member leaving"))

    @logset_member.command(name="update")
    async def logset_member_update(self, ctx: RedContext, *types):
        """Set member update logging

        Available log types:
        name, nickname, roles

        Example:
            !logset guild name roles
        -> Logs member name and role updates, but not nickname changes"""
        _set = await group_set(types, self.config.guild(ctx.guild).members.update)
        msg = "{}\n{}".format(info("Updated member update log settings"), _set)
        await ctx.send(msg)

    @logset.group(name="role")
    async def logset_role(self, ctx: RedContext):
        """Manage role logging"""
        await cmd_help(ctx, "role")

    @logset_role.command(name="create")
    async def logset_role_create(self, ctx: RedContext):
        """Toggle role creation logging"""
        toggled = toggle(self.config.guild(ctx.guild).roles.create)
        if toggled:
            await ctx.send(info("Now logging role creation"))
        else:
            await ctx.send(info("No longer logging role creation"))

    @logset_role.command(name="delete")
    async def logset_role_delete(self, ctx: RedContext):
        """Toggle role deletion logging"""
        toggled = toggle(self.config.guild(ctx.guild).roles.delete)
        if toggled:
            await ctx.send(info("Now logging role deletion"))
        else:
            await ctx.send(info("No longer logging role deletion"))

    @logset_role.command(name="update")
    async def logset_role_update(self, ctx: RedContext, *types):
        """Manage role update logging

        Available log types:
        name, hoist, mention, position, permissions, colour

        Example:
            !logset guild name permissions
        -> Logs role name and permission changes, but not hoist/mentionable status or position changes"""
        _set = await group_set(types, self.config.guild(ctx.guild).roles.update)
        msg = "{}\n{}".format(info("Updated role update log settings"), _set)
        await ctx.send(msg)

    @logset.command(name="voice")
    async def logset_voice(self, ctx: RedContext, *types):
        """Manage voice status logging

        Available types:
        join, leave, switch, selfmute, servermute, selfdeaf, serverdeaf

        Example:
            !logset voice join servermute serverdeaf
        -> Logs channel joining, server mute and deafening, but not self mute/deafens, channel switching or leaving"""
        _set = await group_set(types, self.config.guild(ctx.guild).voice)
        msg = "{}\n{}".format(info("Updated voice status log settings"), _set)
        await ctx.send(msg)

    @logset.command(name="reset")
    async def logset_reset(self, ctx: RedContext):
        """Reset the guild's log settings"""
        await self.config.guild(ctx.guild).clear()
        await ctx.tick()

    ###################
    #    Listeners    #
    ###################

    async def on_message_delete(self, message: discord.Message):
        if isinstance(message.channel, discord.DMChannel):
            return
        if not await self.config.guild(message.guild).messages.delete():
            return
        formatter = await get_formatter(message.guild, self.config.guild(message.guild))
        if not formatter:
            return
        await formatter.send_log_message("messages", "delete", message=message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if isinstance(after.channel, discord.DMChannel):
            return
        if not await self.config.guild(after.guild).messages.edit():
            return
        formatter = await get_formatter(after.guild, self.config.guild(after.guild))
        if not formatter:
            return
        await formatter.send_log_message("messages", "edit", before=before, after=after)

    async def on_member_join(self, member: discord.Member):
        if not await self.config.guild(member.guild).members.join():
            return
        formatter = await get_formatter(member.guild, self.config.guild(member.guild))
        if not formatter:
            return
        await formatter.send_log_message("members", "join", member=member)

    async def on_member_leave(self, member: discord.Member):
        if not await self.config.guild(member.guild).members.leave():
            return
        formatter = await get_formatter(member.guild, self.config.guild(member.guild))
        if not formatter:
            return
        await formatter.send_log_message("members", "leave", member=member)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not await self.config.guild(after.guild).members.update():
            return
        formatter = await get_formatter(after.guild, self.config.guild(after.guild))
        if not formatter:
            return
        await formatter.send_log_message("members", "update", before=before, after=after)

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        if not await self.config.guild(guild).channels.create():
            return
        formatter = await get_formatter(guild, self.config.guild(guild))
        if not formatter:
            return
        await formatter.send_log_message("channels", "create", channel=channel)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        if not await self.config.guild(guild).channels.delete():
            return
        formatter = await get_formatter(guild, self.config.guild(guild))
        if not formatter:
            return
        await formatter.send_log_message("channels", "delete", channel=channel)

    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        guild = before.guild
        formatter = await get_formatter(guild, self.config.guild(guild))
        if not formatter:
            return
        await formatter.send_log_message("channels", "update", before=before, after=after)

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        guild = member.guild
        formatter = await get_formatter(guild, self.config.guild(guild))
        if not formatter:
            return
        await formatter.send_log_message("voice", "update", before=before, after=after, member=member)

    async def on_guild_role_create(self, role: discord.Role):
        if not await self.config.guild(role.guild).roles.create():
            return
        formatter = await get_formatter(role.guild, self.config.guild(role.guild))
        if not formatter:
            return
        await formatter.send_log_message("roles", "create", role=role)

    async def on_guild_role_delete(self, role: discord.Role):
        if not await self.config.guild(role.guild).roles.delete():
            return
        formatter = await get_formatter(role.guild, self.config.guild(role.guild))
        if not formatter:
            return
        await formatter.send_log_message("roles", "delete", role=role)

    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        formatter = await get_formatter(after.guild, self.config.guild(after.guild))
        if not formatter:
            return
        await formatter.send_log_message("roles", "update", before=before, after=after)

    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        formatter = await get_formatter(after, self.config.guild(after))
        if not formatter:
            return
        await formatter.send_log_message("guild", "update", before=before, after=after)
