import discord

from redbot.core.utils.chat_formatting import inline

from logs.core import Module, LogEntry, _


class MessageModule(Module):
    name = "message"
    friendly_name = _("Message")
    description = _("Message edit and deletion logging")
    settings = {
        "edit": _("Message edits"),
        "delete": _("Message deletions")
    }

    def edit(self, before: discord.Message, after: discord.Message):
        return (
            LogEntry(colour=discord.Colour.blurple())
            .set_author(name=_("Message Edited"), icon_url=self.icon_uri(after.author))
            .set_footer(text=_("Message ID: {}").format(after.id))
            .add_field(name=_("Message Author"), value=f"{after.author.mention} ({after.author.id})", inline=True)
            .add_field(name=_("Channel"), value=f"{after.channel.mention} ({after.channel.id})", inline=True)
            .add_differ_field(name=_("Content Diff"), before=before.content, after=after.content)
        ) if all([self.is_opt_enabled("edit"), before.content != after.content, not after.author.bot]) else None

    def delete(self, message: discord.Message):
        return (
            LogEntry(colour=discord.Colour.red())
            .set_author(name=_("Message Deleted"), icon_url=self.icon_uri(message.author))
            .set_footer(text=_("Message ID: {}").format(message.id))
            .add_field(name=_("Message Author"), value=f"{message.author.mention} ({message.author.id})",
                       inline=True)
            .add_field(name=_("Channel"), value=f"{message.channel.mention} ({message.channel.id})", inline=True)
            .add_field(name=_("Content"), value=message.content or inline(_("No message content")))
            # due to how LogEntry.add_field works, this will only display if value is not None
            .add_field(name=_("Attachments"),
                       value="\n".join([f"<{x.url}>" for x in message.attachments])
                             if message.attachments else None)
        ) if all([self.is_opt_enabled("delete"), not message.author.bot]) else None
