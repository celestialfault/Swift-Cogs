import discord

from logs.logentry import LogEntry
from .base import LogType


class ChannelLogType(LogType):
    name = "channels"

    async def update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel, **kwargs):
        settings = await self.guild.config.channels.update()
        ret = LogEntry(self)
        ret.colour = discord.Colour.blurple()
        ret.emoji = "\N{MEMO}"
        ret.title = "Channel updated"
        ret.description = "Channel {0.mention}".format(after)
        # shh pycharm, all is fine
        # noinspection PyUnresolvedReferences
        if before.name != after.name and settings["name"]:
            ret.add_field(title="Channel Name", value="Channel name changed to **{0!s}**".format(after))
        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            if before.topic != after.topic and settings["topic"]:
                ret.add_field(title="Channel Topic", value="Channel topic changed to:\n```\n{0.topic}```".format(after))
        elif isinstance(before, discord.VoiceChannel) and isinstance(after, discord.VoiceChannel):
            if before.bitrate != after.bitrate and settings["bitrate"]:
                ret.add_field(title="Channel Bitrate", value="Channel bitrate changed to {}".format(
                    str(after.bitrate)[:-3] + " kbps"))
            if before.user_limit != after.user_limit and settings["user_limit"]:
                txt = "set to {}".format(after.user_limit) if after.user_limit else "cleared"
                ret.add_field(title="User Limit", value="Channel user limit has been {}".format(txt))
        if before.category != after.category and settings["category"]:
            if after.category:
                ret.add_field(title="Channel Category", value="Channel was moved to category {0!s}".format(
                    after.category))
            else:
                ret.add_field(title="Channel Category", value="Channel was removed from category {0!s}".format(
                    before.category))
        return ret

    def create(self, created: discord.abc.GuildChannel, **kwargs):
        ret = LogEntry(self)
        ret.colour = discord.Colour.green()
        ret.emoji = "\N{LOWER LEFT BALLPOINT PEN}"
        ret.title = "Channel created"
        ret.require_fields = False
        ret.description = "Channel {0.mention} created".format(created)
        return ret

    def delete(self, deleted: discord.abc.GuildChannel, **kwargs):
        ret = LogEntry(self)
        ret.colour = discord.Colour.red()
        ret.title = "Channel deleted"
        ret.emoji = "\N{WASTEBASKET}"
        ret.require_fields = False
        ret.description = "Channel {0!s} deleted".format(deleted)
        return ret
