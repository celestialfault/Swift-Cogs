from datetime import datetime

import discord

from logs.logentry import LogEntry
from ._base import BaseLog


def format_userlimit(user_limit: int = None):
    if user_limit is None or user_limit == 0:
        return "No limit"
    if user_limit == 1:
        return "1 user"
    else:
        return f"{str(user_limit)} users"


class ChannelLog(BaseLog):
    name = "channels"
    descriptions = {
        "create": "Channel creation",
        "delete": "Channel deletion",
        "name": "Channel name",
        "topic": "Text channel topics",
        "category": "Channel category",
        "bitrate": "Voice channel bitrate",
        "user_limit": "Voice channel user limit",
        "position": "Channel position changes (this option can be spammy!)"
    }

    async def update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel, **kwargs):
        embed = LogEntry(colour=discord.Colour.blurple(), timestamp=datetime.utcnow(),
                         description=f"Channel: {after.mention}")
        embed.set_author(name="Channel Updated", icon_url=self.icon_url)

        if hasattr(before, "name") and hasattr(after, "name"):  # you win this time pycharm
            if self.has_changed(before.name, after.name, "name"):
                embed.add_diff_field(name="Channel Name", before=before.name, after=after.name)

        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            if self.has_changed(before.topic, after.topic, "topic"):
                embed.add_diff_field(name="Channel Topic", before=before.topic, after=after.topic, description="")

        elif isinstance(before, discord.VoiceChannel) and isinstance(after, discord.VoiceChannel):
            if self.has_changed(before.bitrate, after.bitrate, "bitrate"):
                # noinspection PyUnresolvedReferences
                embed.add_diff_field(name="Channel Bitrate", before=f"{str(before.bitrate)[:-3]} kbps",
                                     after=f"{str(after.bitrate)[:-3]} kbps")

            if self.has_changed(before.user_limit, after.user_limit, "user_limit"):
                embed.add_diff_field(name="User Limit", before=format_userlimit(before.user_limit),
                                     after=format_userlimit(after.user_limit))

        if self.has_changed(before.category, after.category, "category"):
            embed.add_diff_field(name="Channel Category", before=getattr(before.category, "name", "Uncategorized"),
                                 after=getattr(after.category, "name", "Uncategorized"))

        if self.has_changed(before.position, after.position, "position"):
            embed.add_diff_field(name="Channel Position", before=before.position, after=after.position)

        return embed

    def create(self, created: discord.abc.GuildChannel, **kwargs):
        if not self.settings.get("create", False):
            return None
        return LogEntry(colour=discord.Colour.green(), title="Channel Created", timestamp=datetime.utcnow(),
                        description=f"Channel {created.mention} created", require_fields=False)

    def delete(self, deleted: discord.abc.GuildChannel, **kwargs):
        if not self.settings.get("delete", False):
            return None

        return LogEntry(colour=discord.Colour.red(), title="Channel Deleted", timestamp=datetime.utcnow(),
                        description=f"Channel {deleted!s} deleted", require_fields=False)
