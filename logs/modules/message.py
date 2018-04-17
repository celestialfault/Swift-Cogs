from typing import List

import discord
from discord.raw_models import RawBulkMessageDeleteEvent

from redbot.core.utils.chat_formatting import inline

from logs.core import Module, LogEntry, _


class MessageModule(Module):
    name = "message"
    friendly_name = _("Message")
    description = _("Message edit and deletion logging")
    settings = {
        "edit": _("Message edits"),
        "delete": _("Message deletions"),
        "bulkdelete": _("Bulk message deletions")
    }

    async def edit(self, before: discord.Message, after: discord.Message):
        return (
            LogEntry(colour=discord.Colour.blurple(), ignore_fields=['Message Author', 'Channel'])
            .set_author(name=_("Message Edited"), icon_url=self.icon_uri(after.author))
            .set_footer(text=_("Message ID: {}").format(after.id))
            .add_field(name=_("Message Author"), inline=True,
                       value="{after.author.mention} ({after.author.id})".format(after=after))
            .add_field(name=_("Channel"), inline=True,
                       value="{after.channel.mention} ({after.channel.id})".format(after=after))
            .add_differ_field(name=_("Content Diff"), before=before.content, after=after.content)
        ) if all([await self.is_opt_enabled("edit"), before.content != after.content, not after.author.bot]) else None

    async def delete(self, message: discord.Message):
        return (
            LogEntry(colour=discord.Colour.red(), ignore_fields=['Message Author', 'Channel'])
            .set_author(name=_("Message Deleted"), icon_url=self.icon_uri(message.author))
            .set_footer(text=_("Message ID: {}").format(message.id))
            .add_field(name=_("Message Author"), inline=True,
                       value="{message.author.mention} ({message.author.id})".format(message=message))
            .add_field(name=_("Channel"), inline=True,
                       value="{message.channel.mention} ({message.channel.id})".format(message=message))
            .add_field(name=_("Content"), value=message.content or inline(_("No message content")))
            # due to how LogEntry.add_field works, this will only display if value is not None
            .add_field(name=_("Attachments"),
                       value="\n".join(["<{.url}>".format(x) for x in message.attachments])
                             if message.attachments else None)
        ) if all([await self.is_opt_enabled("delete"), not message.author.bot]) else None

    async def bulk_delete(self, channel: discord.TextChannel, message_ids: List[int]):
        if not message_ids:
            return None
        return (
            LogEntry(colour=discord.Colour.dark_red(),
                     description=_("{count} message(s) were deleted from channel {channel}").format(
                         count=len(message_ids), channel=channel.mention), require_fields=False)
            .set_author(name=_("Message Bulk Deletion"), icon_url=self.icon_uri())
        ) if await self.is_opt_enabled("bulkdelete") else None
