import discord
from discord.ext import commands

from redbot.core.bot import Red, RedContext
from redbot.core import checks, Config

from .embeds import *
from .utils import (
    is_ignored,
    toggle_setting,
    validate_log_channel,
    send_log_message
)


class Logs:
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5678913563, force_registration=True)

        defaults_guild = {
            "ignored": False,
            "channels": {
                "guild": None,
                "members": None,
                "messages": None,
                "voice": None
            },
            "members": {
                "join": False,
                "leave": False,
                "update": False
            },
            "guild": {
                # "role_create": False,
                # "role_delete": False,
                # "role_update": False,
                "channel_create": False,
                "channel_delete": False,
                "channel_update": False
            },
            "voice": {
                "join_part": False,
                "mute_unmute": False,
                "deafen_undeafen": False
            },
            "messages": {
                "edit": False,
                "delete": False
            }
        }

        defaults_member_channel = {
            "ignored": False
        }

        self.config.register_guild(**defaults_guild)
        self.config.register_member(**defaults_member_channel)
        self.config.register_channel(**defaults_member_channel)

    @commands.group(name="logs", aliases=["logset"])
    @commands.guild_only()
    @checks.guildowner_or_permissions(manage_server=True)
    async def logset(self, ctx: RedContext):
        """
        Manage guild log settings
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    ###################
    #    Channels     #
    ###################

    @logset.group(name="logchannel")
    async def logset_channel(self, ctx: RedContext):
        """
        Manage log channels
        """
        if not ctx.invoked_subcommand or (ctx.invoked_subcommand and ctx.invoked_subcommand.name == "logchannel"):
            await ctx.send_help()

    @logset_channel.command(name="all")
    async def logset_channel_all(self, ctx: RedContext, channel: discord.TextChannel=None):
        """
        Set or clear all log channels
        """
        if not await validate_log_channel(channel, ctx.guild):
            await ctx.send("❌ I can't log to that channel")
            return
        _channel = channel.id if channel else None
        await self.config.guild(ctx.guild).channels.set({
            "guild": _channel,
            "members": _channel,
            "messages": _channel,
            "voice": _channel
        })
        if channel:
            await ctx.send("✅ Set all log channels to {}".format(channel.mention), delete_after=15)
        else:
            await ctx.send("✅ Cleared all previously set log channels", delete_after=15)

    @logset_channel.command(name="guild", aliases=["server"])
    async def logset_channel_guild(self, ctx: RedContext, channel: discord.TextChannel=None):
        """
        Set the log channel for guild events
        """
        if not await validate_log_channel(channel, ctx.guild):
            await ctx.send("❌ I can't log to that channel")
            return
        await self.config.guild(ctx.guild).channels.guild.set(channel.id if channel else None)
        if channel:
            await ctx.send("✅ Set guild event log channel to {}".format(channel.mention), delete_after=15)
        else:
            await ctx.send("✅ Cleared previously set guild event channel", delete_after=15)

    @logset_channel.command(name="members")
    async def logset_channel_member(self, ctx: RedContext, channel: discord.TextChannel=None):
        """
        Set the log channel for member events
        """
        if not await validate_log_channel(channel, ctx.guild):
            await ctx.send("❌ I can't log to that channel")
            return
        await self.config.guild(ctx.guild).channels.members.set(channel.id if channel else None)
        if channel:
            await ctx.send("✅ Set member event log channel to {}".format(channel.mention), delete_after=15)
        else:
            await ctx.send("✅ Cleared previously set member event channel", delete_after=15)

    @logset_channel.command(name="messages")
    async def logset_channel_messages(self, ctx: RedContext, channel: discord.TextChannel=None):
        """
        Set the log channel for message events
        """
        if not await validate_log_channel(channel, ctx.guild):
            await ctx.send("❌ I can't log to that channel")
            return
        await self.config.guild(ctx.guild).channels.messages.set(channel.id if channel else None)
        if channel:
            await ctx.send("✅ Set message event log channel to {}".format(channel.mention), delete_after=15)
        else:
            await ctx.send("✅ Cleared previously set message event channel", delete_after=15)

    @logset_channel.command(name="voice")
    async def logset_channel_voice(self, ctx: RedContext, channel: discord.TextChannel=None):
        """
        Set the log channel for voice events
        """
        if not await validate_log_channel(channel, ctx.guild):
            await ctx.send("❌ I can't log to that channel")
            return
        await self.config.guild(ctx.guild).channels.voice.set(channel.id if channel else None)
        if channel:
            await ctx.send("✅ Set voice event log channel to {}".format(channel.mention), delete_after=15)
        else:
            await ctx.send("✅ Cleared previously set voice event channel", delete_after=15)

    ###################
    #     Members     #
    ###################

    @logset.group(name="member")
    async def logset_member(self, ctx: RedContext):
        """
        Manage member event logging
        """
        if not ctx.invoked_subcommand or (ctx.invoked_subcommand and ctx.invoked_subcommand.name == "member"):
            await ctx.send_help()

    @logset_member.command(name="join")
    async def logset_member_join(self, ctx: RedContext, toggle: bool=None):
        """
        Toggles member join logging
        """
        toggle = await toggle_setting(self.config.guild(ctx.guild).members.join, toggle)
        if toggle:
            await ctx.send("✅ Enabled member join logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled member join logging", delete_after=15)

    @logset_member.command(name="update")
    async def logset_member_update(self, ctx: RedContext, toggle: bool=None):
        """
        Toggles member update logging (such as names, nicknames and role changes)
        """
        toggle = await toggle_setting(self.config.guild(ctx.guild).members.update, toggle)
        if toggle:
            await ctx.send("✅ Enabled member update logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled member update logging", delete_after=15)

    ###################
    #      Guild      #
    ###################

    @logset.group(name="guild", alias=["server"])
    async def logset_guild(self, ctx: RedContext):
        """
        Manage guild event logging
        """
        if not ctx.invoked_subcommand or (ctx.invoked_subcommand and ctx.invoked_subcommand.name == "guild"):
            await ctx.send_help()

    @logset_guild.group(name="roles", hidden=True)
    async def logset_guild_roles(self, ctx: RedContext):
        """
        Manage role event logging
        """
        if ctx.invoked_subcommand.name == "roles":
            await ctx.send_help()

    @logset_guild_roles.command(name="create")
    async def logset_guild_roles_create(self, ctx: commands.Context, toggle: bool=None):
        """
        Toggles role creation logging
        """
        toggle = await toggle_setting(self.config.guild(ctx.guild).guild.role_create, toggle)
        if toggle:
            await ctx.send("✅ Enabled role creation logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled role creation logging", delete_after=15)

    @logset_guild_roles.command(name="delete")
    async def logset_guild_roles_delete(self, ctx: commands.Context, toggle: bool=None):
        """
        Toggles role deletion logging
        """
        toggle = await toggle_setting(self.config.guild(ctx.guild).guild.role_delete, toggle)
        if toggle:
            await ctx.send("✅ Enabled role deletion logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled role deletion logging", delete_after=15)

    @logset_guild_roles.command(name="update")
    async def logset_guild_roles_update(self, ctx: RedContext, toggle: bool=None):
        """
        Toggles role update logging
        """
        toggle = await toggle_setting(self.config.guild(ctx.guild).guild.role_update, toggle)
        if toggle:
            await ctx.send("✅ Enabled role update logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled role update logging", delete_after=15)

    @logset_guild.group(name="channel")
    async def logset_guild_channel(self, ctx: RedContext):
        """
        Manage channel event logging
        """
        if ctx.invoked_subcommand and ctx.invoked_subcommand.name == "channel":
            await ctx.send_help()

    @logset_guild_channel.command(name="create")
    async def logset_guild_channel_create(self, ctx: RedContext, toggle: bool=None):
        """
        Toggles channel creation logging
        """
        toggle = await toggle_setting(self.config.guild(ctx.guild).guild.channel_create, toggle)
        if toggle:
            await ctx.send("✅ Enabled channel creation logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled channel creation logging", delete_after=15)

    @logset_guild_channel.command(name="delete")
    async def logset_guild_channel_delete(self, ctx: RedContext, toggle: bool=None):
        """
        Toggles channel deletion logging
        """
        toggle = await toggle_setting(self.config.guild(ctx.guild).guild.channel_delete, toggle)
        if toggle:
            await ctx.send("✅ Enabled channel deletion logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled channel deletion logging", delete_after=15)

    @logset_guild_channel.command(name="update")
    async def logset_guild_channel_update(self, ctx: RedContext, toggle: bool=None):
        """
        Toggles channel update logging
        """
        toggle = await toggle_setting(self.config.guild(ctx.guild).guild.channel_update, toggle)
        if toggle:
            await ctx.send("✅ Enabled channel update logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled channel update logging", delete_after=15)

    ###################
    #    Messages     #
    ###################

    @logset.group(name="message")
    async def logset_message(self, ctx: RedContext):
        """
        Manage message event logging
        """
        if not ctx.invoked_subcommand or (ctx.invoked_subcommand and ctx.invoked_subcommand.name == "message"):
            await ctx.send_help()

    @logset_message.command(name="edit")
    async def logset_message_edit(self, ctx: RedContext, toggle: bool=None):
        """
        Toggles message edit logs
        """
        toggle = toggle if toggle is not None else not await self.config.guild(ctx.guild).messages.edit()
        await self.config.guild(ctx.guild).messages.edit.set(toggle)
        if toggle:
            await ctx.send("✅ Enabled message edit logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled message edit logging", delete_after=15)

    @logset_message.command(name="delete")
    async def logset_message_delete(self, ctx: RedContext, toggle: bool=None):
        """
        Toggles message deletion logs
        """
        toggle = toggle if toggle is not None else not await self.config.guild(ctx.guild).messages.delete()
        await self.config.guild(ctx.guild).messages.delete.set(toggle)
        if toggle:
            await ctx.send("✅ Enabled message deletion logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled message deletion logging", delete_after=15)

    ###################
    #      Voice      #
    ###################

    @logset.group(name="voice")
    async def logset_voice(self, ctx: RedContext):
        """
        Manage voice event logging
        """
        if not ctx.invoked_subcommand or (ctx.invoked_subcommand and ctx.invoked_subcommand.name == "voice"):
            await ctx.send_help()

    @logset_voice.command(name="channel", aliases=["join", "part", "joinpart"])
    async def logset_voice_joinpart(self, ctx: RedContext, toggle: bool=None):
        """
        Toggles logging of voice channel joins, parts and switching
        """
        toggle = await toggle_setting(self.config.guild(ctx.guild).voice.join_part, toggle)
        if toggle:
            await ctx.send("✅ Enabled voice channel logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled voice channel logging", delete_after=15)

    @logset_voice.command(name="mute", aliases=["unmute"])
    async def logset_voice_mute(self, ctx: RedContext, toggle: bool=None):
        """
        Toggles logging of voice mute and unmute status
        """
        toggle = await toggle_setting(self.config.guild(ctx.guild).voice.mute_unmute, toggle)
        if toggle:
            await ctx.send("✅ Enabled voice mute status logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled voice mute status logging", delete_after=15)

    @logset_voice.command(name="deafen", aliases=["undeafen", "deaf"])
    async def logset_voice_deafen(self, ctx: RedContext, toggle: bool = None):
        """
        Toggles logging of voice mute and unmute status
        """
        toggle = await toggle_setting(self.config.guild(ctx.guild).voice.deafen_undeafen, toggle)
        if toggle:
            await ctx.send("✅ Enabled voice deaf status logging", delete_after=15)
        else:
            await ctx.send("✅ Disabled voice deaf status logging", delete_after=15)

    ###################
    #     Ignores     #
    ###################

    @logset.group(name="ignore")
    async def logset_ignore(self, ctx: RedContext):
        """
        Ignore channels and members from logging
        """
        if not ctx.invoked_subcommand or (ctx.invoked_subcommand and ctx.invoked_subcommand.name == "ignore"):
            await ctx.send_help()

    @logset_ignore.command(name="member")
    async def logset_ignore_member(self, ctx: RedContext, member: discord.Member):
        """
        Toggles a user's logging ignore status
        """
        toggle = not await self.config.member(member).ignored()
        await self.config.member(member).ignored.set(toggle)
        member_name = escape(str(member), mass_mentions=True, formatting=True)
        if toggle:
            await ctx.send("✅ **{}** is now ignored from logging".format(member_name))
        else:
            await ctx.send("✅ **{}** is no longer ignored from logging".format(member_name))

    @logset_ignore.command(name="channel")
    async def logset_ignore_channel(self, ctx: RedContext, channel: discord.TextChannel):
        """
        Ignores a channel from logging
        """
        toggle = not await self.config.channel(channel).ignored()
        await self.config.channel(channel).ignored.set(toggle)
        if toggle:
            await ctx.send("✅ All events in {} will no longer be logged".format(channel.mention))
        else:
            await ctx.send("✅ All events in {} will now be logged".format(channel.mention))

    @logset_ignore.command(name="guild")
    @checks.is_owner()
    async def logset_ignore_server(self, ctx: RedContext, guild: discord.Guild=None):
        """
        Ignores an entire guild from logging
        """
        if not guild:
            guild = ctx.guild
        toggle = not await self.config.guild(guild).ignored()
        await self.config.guild(guild).ignored.set(toggle)
        if toggle:
            await ctx.send("✅ Now ignoring `{}`".format(guild.name), delete_after=15)
        else:
            await ctx.send("✅ No longer ignoring `{}`".format(guild.name), delete_after=15)

    ###################
    #    Listeners    #
    ###################

    async def on_message_delete(self, message: discord.Message):
        if isinstance(message.channel, discord.DMChannel) or \
                await is_ignored(self.config, message.author, message.guild, message.channel):
            return
        if not await self.config.guild(message.guild).messages.delete():
            return
        log_channel = self.bot.get_channel(await self.config.guild(message.guild).channels.messages())
        await send_log_message(log_channel, embed_message_delete, message=message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if isinstance(after.channel, discord.DMChannel) or\
                await is_ignored(self.config, after.author, after.guild, after.channel):
            return
        if not await self.config.guild(after.guild).messages.edit():
            return
        log_channel = self.bot.get_channel(await self.config.guild(after.guild).channels.messages())
        await send_log_message(log_channel, embed_message_edit, before=before, after=after)

    async def on_member_join(self, member: discord.Member):
        if await is_ignored(self.config, member, member.guild, None):
            return
        if not await self.config.guild(member.guild).members.join():
            return
        log_channel = self.bot.get_channel(await self.config.guild(member.guild).channels.members())
        await send_log_message(log_channel, embed_member_join, member=member)

    async def on_member_leave(self, member: discord.Member):
        if await is_ignored(self.config, member, member.guild, None):
            return
        if not await self.config.guild(member.guild).members.leave():
            return
        log_channel = self.bot.get_channel(await self.config.guild(member.guild).channels.members())
        await send_log_message(log_channel, embed_member_leave, member=member)

    async def on_member_update(self, before: Member, after: Member):
        if await is_ignored(self.config, after, after.guild, None):
            return
        if not await self.config.guild(after.guild).members.update():
            return
        log_channel = self.bot.get_channel(await self.config.guild(after.guild).channels.members())
        await send_log_message(log_channel, embed_member_update, before=before, after=after)

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        if not await self.config.guild(guild).guild.channel_create():
            return
        log_channel = self.bot.get_channel(await self.config.guild(guild).channels.guild())
        await send_log_message(log_channel, embed_channel_create, channel=channel)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        if not await self.config.guild(guild).guild.channel_delete():
            return
        log_channel = self.bot.get_channel(await self.config.guild(guild).channels.guild())
        await send_log_message(log_channel, embed_channel_delete, channel=channel)

    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        guild = before.guild
        if not await self.config.guild(guild).guild.channel_update():
            return
        log_channel = self.bot.get_channel(await self.config.guild(guild).channels.guild())
        await send_log_message(log_channel, embed_channel_update, before=before, after=after)

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        if await is_ignored(self.config, member, member.guild, None):
            return
        if not await self.config.guild(member.guild).messages.edit():
            return
        log_channel = self.bot.get_channel(await self.config.guild(member.guild).channels.voice())
        await send_log_message(log_channel, embed_voice, member=member, before=before, after=after,
                               config=self.config.guild(member.guild).voice)
