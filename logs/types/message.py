from datetime import datetime

import discord

from logs.logentry import LogEntry
from ._base import BaseLogType, _


class MessageLogType(BaseLogType):
    name = "messages"
    descriptions = {
        "edit": _("Message edits"),
        "delete": _("Message deletions")
    }

    def create(self, created, **kwargs):
        return NotImplemented

    def update(self, before: discord.Message, after: discord.Message, **kwargs):
        if any([after.author.bot, after.type != discord.MessageType.default,
                before.content == after.content, self.settings.get("edit", False) is False]):
            return None

        author = after.author
        channel = after.channel

        embed = LogEntry(colour=discord.Colour.blurple(), timestamp=datetime.utcnow())
        embed.set_author(name=_("Message Edited"), icon_url=self.icon_url(author))
        embed.set_footer(text=_("Message ID: {}").format(after.id))

        embed.add_field(name=_("Message Author"), value=f"{author.mention} ({author.id})", inline=True)
        embed.add_field(name=_("Channel"), value=f"{channel.mention} ({channel.id})", inline=True)
        embed.add_differ_field(name=_("Content"), before=before.content, after=after.content)
        return embed

    def delete(self, deleted: discord.Message, **kwargs):
        if any([deleted.author.bot, deleted.type != discord.MessageType.default,
                self.settings.get("delete", False) is False]):
            return None

        author = deleted.author
        channel = deleted.channel

        embed = LogEntry(colour=discord.Colour.red(), timestamp=datetime.utcnow())
        embed.set_author(name=_("Message Deleted"), icon_url=self.icon_url(author))
        embed.set_footer(text=_("Message ID: {}").format(deleted.id))

        embed.add_field(name=_("Message Author"), value=f"{author.mention} ({author.id})", inline=True)
        embed.add_field(name=_("Channel"), value=f"{channel.mention} ({channel.id})", inline=True)
        embed.add_field(name=_("Message Content"), value=deleted.content or _("No message content"))
        if len(deleted.attachments):
            embed.add_field(name=_("Attachments"), value="\n".join(f"<{x.url}>" for x in deleted.attachments))
        return embed
