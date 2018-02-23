from datetime import datetime

import discord

from logs.logentry import LogEntry
from ._base import BaseLog


def format_bitrate(bitrate: int):
    bitrate = str(bitrate)[:-3]
    return f"{bitrate} kbps"


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
        ret = LogEntry(self, colour=discord.Colour.blurple())
        ret.set_title(title="Channel Updated", emoji="\N{MEMO}")
        ret.set_footer(timestamp=datetime.utcnow())
        ret.description = f"Channel: {after.mention}"

        if hasattr(before, "name") and hasattr(after, "name"):  # you win this time pycharm
            if before.name != after.name and self.settings.get("name", False):
                ret.add_diff_field(title="Channel Name", before=before.name, after=after.name)

        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            if before.topic != after.topic and self.settings.get("topic", False):
                ret.add_diff_field(title="Channel Topic", before=before.topic, after=after.topic, box_lang="")

        elif isinstance(before, discord.VoiceChannel) and isinstance(after, discord.VoiceChannel):
            if before.bitrate != after.bitrate and self.settings.get("bitrate", False):
                ret.add_diff_field("Channel Bitrate",
                                   before=format_bitrate(before.bitrate),
                                   after=format_bitrate(after.bitrate))

            if before.user_limit != after.user_limit and self.settings.get("user_limit", False):
                ret.add_diff_field(title="User Limit",
                                   before=format_userlimit(before.user_limit),
                                   after=format_userlimit(after.user_limit))

        if before.category != after.category and self.settings.get("category", False):
            ret.add_diff_field(title="Channel Category",
                               before=before.category.name if before.category is not None else "Uncategorized",
                               after=after.category.name if after.category is not None else "Uncategorized")

        if before.position != after.position and self.settings.get("position", False):
            ret.add_diff_field(title="Channel Position", before=before.position, after=after.position)
        return ret

    def create(self, created: discord.abc.GuildChannel, **kwargs):
        if not self.settings.get("create", False):
            return None

        ret = LogEntry(self, colour=discord.Colour.green(), require_fields=False)
        ret.set_title(title="Channel Created", emoji="\N{LOWER LEFT BALLPOINT PEN}")
        ret.set_footer(timestamp=datetime.utcnow())
        ret.description = f"Channel {created.mention} created"
        return ret

    def delete(self, deleted: discord.abc.GuildChannel, **kwargs):
        if not self.settings.get("delete", False):
            return None

        ret = LogEntry(self, colour=discord.Colour.red(), require_fields=False)
        ret.set_title(title="Channel Deleted", emoji="\N{WASTEBASKET}")
        ret.set_footer(timestamp=datetime.utcnow())
        ret.description = f"Channel {str(deleted)} deleted"
        return ret
