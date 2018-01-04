from datetime import datetime

import discord

from logs.logentry import LogEntry
from .base import LogType


class MessageLogType(LogType):
    name = "messages"

    def update(self, before: discord.Message, after: discord.Message, **kwargs):
        if after.author.bot:
            return None
        if after.type != discord.MessageType.default:
            return None
        if before.content == after.content:
            return None
        ret = LogEntry(self, title="Message edited", emoji="\N{MEMO}", colour=discord.Colour.blurple(),
                       timestamp=datetime.utcnow())
        ret.description = "Message author: **{0!s}** ({0.id})".format(after.author)
        ret.icon_url = after.author.avatar_url
        before_content = before.content
        if len(before_content) > 750:
            before_content = before_content[:750] + "*...*"
        after_content = after.content
        if len(after_content) > 750:
            after_content = after_content[:750] + "*...*"
        ret.add_field(title="Previous content", value=before_content)
        ret.add_field(title="New content", value=after_content)
        return ret

    def create(self, created, **kwargs):
        raise NotImplementedError

    def delete(self, deleted: discord.Message, **kwargs):
        if deleted.author.bot:
            return None
        if deleted.type != discord.MessageType.default:
            return None
        ret = LogEntry(self, title="Message deleted", emoji="\N{WASTEBASKET}", colour=discord.Colour.red(),
                       timestamp=datetime.utcnow())
        ret.icon_url = deleted.author.avatar_url
        ret.description = "Message author: **{0!s}** ({0.id})".format(deleted.author)
        ret.add_field(title="Message content", value=deleted.content[:1500] or "*No message content*")
        if len(deleted.attachments):
            ret.add_field(title="Attachments", value="\n".join("<{0}>".format(x.url) for x in deleted.attachments))
        return ret
