from typing import List

import discord

from redbot.core.utils.chat_formatting import inline

from logs.core import Module, LogEntry, i18n


class MessageModule(Module):
    name = "message"
    friendly_name = i18n("Message")
    description = i18n("Message edit and deletion logging")
    settings = {
        "edit": i18n("Message edits"),
        "delete": i18n("Message deletions"),
        "bulkdelete": i18n("Bulk message deletions"),
    }

    async def edit(self, before: discord.Message, after: discord.Message):
        if not await self.is_opt_enabled("edit"):
            return None
        if after.author.bot:
            return None

        embed = LogEntry(
            self, colour=discord.Colour.blurple(), ignore_fields=["Message Author", "Channel"]
        )
        embed.set_author(name=i18n("Message Edited"), icon_url=self.icon_uri(after.author))
        embed.set_footer(text=i18n("Message ID: {}").format(after.id))
        embed.add_field(
            name=i18n("Message Author"),
            inline=True,
            value="{after.author.mention} ({after.author.id})".format(after=after),
        )
        embed.add_field(
            name=i18n("Channel"),
            inline=True,
            value="{after.channel.mention} ({after.channel.id})".format(after=after),
        )
        await embed.add_if_changed(
            name=i18n("Content Diff"), before=before.content, after=after.content, diff=True
        )
        return embed

    async def delete(self, message: discord.Message):
        return (
            LogEntry(
                self, colour=discord.Colour.red(), ignore_fields=["Message Author", "Channel"]
            ).set_author(
                name=i18n("Message Deleted"), icon_url=self.icon_uri(message.author)
            ).set_footer(
                text=i18n("Message ID: {}").format(message.id)
            ).add_field(
                name=i18n("Message Author"),
                inline=True,
                value="{message.author.mention} ({message.author.id})".format(message=message),
            ).add_field(
                name=i18n("Channel"),
                inline=True,
                value="{message.channel.mention} ({message.channel.id})".format(message=message),
            ).add_field(
                name=i18n("Content"), value=message.content or inline(i18n("No message content"))
            )
            # due to how LogEntry.add_field works, this will only display if value is not None
            .add_field(
                name=i18n("Attachments"),
                value="\n".join(["<{.url}>".format(x) for x in message.attachments])
                if message.attachments
                else None,
            )
        ) if all(
            [await self.is_opt_enabled("delete"), not message.author.bot]
        ) else None

    async def bulk_delete(self, channel: discord.TextChannel, message_ids: List[int]):
        if not message_ids:
            return None
        return (
            LogEntry(
                self,
                colour=discord.Colour.dark_red(),
                description=i18n("{count} message(s) were deleted from channel {channel}").format(
                    count=len(message_ids), channel=channel.mention
                ),
                require_fields=False,
            ).set_author(
                name=i18n("Message Bulk Deletion"), icon_url=self.icon_uri()
            )
        ) if await self.is_opt_enabled(
            "bulkdelete"
        ) else None
