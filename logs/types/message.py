from datetime import datetime

import discord

from logs.logentry import LogEntry
from ._base import BaseLog


class MessageLog(BaseLog):
    name = "messages"
    descriptions = {
        "edit": "Message edits",
        "delete": "Message deletions"
    }

    def update(self, before: discord.Message, after: discord.Message, **kwargs):
        if any([after.author.bot, after.type != discord.MessageType.default,
                before.content == after.content, self.settings.get("edit", False) is False]):
            return None

        author = after.author
        channel = after.channel
        embed = LogEntry(colour=discord.Colour.blurple(),
                         description=f"Message author: {author.mention} ({author.id})\n"
                                     f"Channel: {channel.mention}",
                         timestamp=datetime.utcnow())

        embed.set_author(name="Message Edited", icon_url=after.author.avatar_url_as(format="png"))
        embed.set_footer(text=f"Message ID: {after.id}")

        embed.add_field(name="Previous Content", value=before.content)
        embed.add_field(name="New Content", value=after.content)
        return embed

    def delete(self, deleted: discord.Message, **kwargs):
        if any([deleted.author.bot, deleted.type != discord.MessageType.default,
                self.settings.get("delete", False) is False]):
            return None

        author = deleted.author
        channel = deleted.channel
        ret = LogEntry(colour=discord.Colour.red(),
                       description=f"Message author: {author.mention} ({author.id})\n"
                                   f"Channel: {channel.mention}",
                       timestamp=datetime.utcnow())

        ret.set_author(name="Message Deleted", icon_url=deleted.author.avatar_url_as(format="png"))
        ret.set_footer(text=f"Message ID: {deleted.id}")

        ret.add_field(name="Message Content", value=deleted.content or "*No message content*")
        if len(deleted.attachments):
            ret.add_field(name="Attachments", value="\n".join(f"<{x.url}>" for x in deleted.attachments))
        return ret

    def create(self, **kwargs):
        return NotImplemented
