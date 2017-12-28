import discord

from logs.logentry import LogEntry
from .base import LogType


class MessageLogType(LogType):
    name = "messages"

    def update(self, before: discord.Message, after: discord.Message, **kwargs):
        if after.author.bot:
            return None
        if before.content == after.content:
            return None
        ret = LogEntry(self)
        ret.title = "Message edited"
        ret.emoji = "\N{MEMO}"
        ret.icon_url = after.author.avatar_url
        ret.colour = discord.Colour.blurple()
        ret.description = "Message author: **{0!s}** ({0.id})".format(after.author)
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
        ret = LogEntry(self)
        ret.title = "Message deleted"
        ret.emoji = "\N{WASTEBASKET}"
        ret.icon_url = deleted.author.avatar_url
        ret.colour = discord.Colour.red()
        ret.description = "Message author: **{0!s}** ({0.id})".format(deleted.author)
        ret.add_field(title="Message content", value=deleted.content[:1600] or "*No message content*")
        return ret
