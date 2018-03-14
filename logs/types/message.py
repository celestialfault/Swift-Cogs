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

        author = after.author
        channel = after.channel
        embed = LogEntry(colour=discord.Colour.blurple(), timestamp=datetime.utcnow())

        embed.set_author(name="Message Edited", icon_url=after.author.avatar_url_as(format="png"))
        embed.set_footer(text=f"Message ID: {after.id}")

        embed.add_field(name="Message Author", value=f"{author.mention} ({author.id})", inline=True)
        embed.add_field(name="Channel", value=f"{channel.mention} ({channel.id})", inline=True)
        embed.add_differ_field(name="Content", before=before.content, after=after.content)
        return embed

    def delete(self, deleted: discord.Message, **kwargs):
        if any([deleted.author.bot, deleted.type != discord.MessageType.default,
                self.settings.get("delete", False) is False]):
            return None

        author = deleted.author
        channel = deleted.channel
        embed = LogEntry(colour=discord.Colour.red(), timestamp=datetime.utcnow())

        embed.set_author(name="Message Deleted", icon_url=deleted.author.avatar_url_as(format="png"))
        embed.set_footer(text=f"Message ID: {deleted.id}")

        embed.add_field(name="Message Author", value=f"{author.mention} ({author.id})", inline=True)
        embed.add_field(name="Channel", value=f"{channel.mention} ({channel.id})", inline=True)
        embed.add_field(name="Message Content", value=deleted.content or "*No message content*")
        if len(deleted.attachments):
            embed.add_field(name="Attachments", value="\n".join(f"<{x.url}>" for x in deleted.attachments))
        return embed
