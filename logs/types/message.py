from datetime import datetime

import discord

from logs.logentry import LogEntry
from .base import LogType


class MessageLogType(LogType):
    name = "messages"

    def update(self, before: discord.Message, after: discord.Message, **kwargs):
        if after.author.bot:  # Don't log bot messages
            return None
        if after.type != discord.MessageType.default:  # Don't log message edits of non-default types
            return None
        if before.content == after.content:  # Ensure the message content actually changed
            return None

        ret = LogEntry(self, colour=discord.Colour.blurple())
        ret.set_title(title="Message edited", emoji="\N{MEMO}", icon_url=after.author.avatar_url)
        ret.set_footer(footer="Message ID: {0.id}".format(after), timestamp=datetime.utcnow())
        ret.description = "Message author: **{0!s}** ({0.id})".format(after.author)

        ret.add_field(title="Previous Content", value=before.content)
        ret.add_field(title="New Content", value=after.content)
        return ret

    def create(self, created, **kwargs):
        raise NotImplementedError

    def delete(self, deleted: discord.Message, **kwargs):
        if deleted.author.bot:  # Don't log bot messages
            return None
        if deleted.type != discord.MessageType.default:  # Don't log message deletions of non-default types
            return None

        ret = LogEntry(self, colour=discord.Colour.red())
        ret.set_title(title="Message deleted", emoji="\N{WASTEBASKET}", icon_url=deleted.author.avatar_url)
        ret.set_footer(footer="Message ID: {0.id}".format(deleted), timestamp=datetime.utcnow())

        ret.description = "Message author: **{0!s}** ({0.id})".format(deleted.author)
        ret.add_field(title="Message content", value=deleted.content or "*No message content*")
        if len(deleted.attachments):
            ret.add_field(title="Attachments", value="\n".join("<{0}>".format(x.url) for x in deleted.attachments))
        return ret
