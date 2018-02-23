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

    def create(self, created, **kwargs):
        return NotImplemented

    def update(self, before: discord.Message, after: discord.Message, **kwargs):
        if any([after.author.bot, after.type != discord.MessageType.default,
                before.content == after.content, self.settings.get("edit", False) is False]):
            return None

        ret = LogEntry(self, colour=discord.Colour.blurple())
        author = after.author
        ret.description = f"Message author: **{author!s}** ({author.id})\nChannel: {after.channel.mention}"

        ret.set_title(title="Message Edited", emoji="\N{MEMO}", icon_url=after.author.avatar_url)
        ret.set_footer(footer=f"Message ID: {after.id}", timestamp=datetime.utcnow())

        ret.add_field(title="Previous Content", value=before.content)
        ret.add_field(title="New Content", value=after.content)
        return ret

    def delete(self, deleted: discord.Message, **kwargs):
        if any([deleted.author.bot, deleted.type != discord.MessageType.default,
                self.settings.get("delete", False) is False]):
            return None

        author = deleted.author
        ret = LogEntry(self, colour=discord.Colour.red())
        ret.description = f"Message author: **{author!s}** ({author.id})\nChannel: {deleted.channel.mention}"

        ret.set_title(title="Message Deleted", emoji="\N{WASTEBASKET}", icon_url=deleted.author.avatar_url)
        ret.set_footer(footer=f"Message ID: {deleted.id}", timestamp=datetime.utcnow())

        ret.add_field(title="Message Content", value=deleted.content or "*No message content*")
        if len(deleted.attachments):
            ret.add_field(title="Attachments", value="\n".join(f"<{x.url}>" for x in deleted.attachments))
        return ret
