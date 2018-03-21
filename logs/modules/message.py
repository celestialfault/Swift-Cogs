import discord

from redbot.core.utils.chat_formatting import inline

from logs.core import Module, LogEntry, _


class MessageModule(Module):
    name = "message"
    friendly_name = _("Message")
    defaults = {
        "edit": False,
        "delete": False
    }
    module_description = _("Message edit and deletion logging")
    option_descriptions = {
        "edit": _("Message edits"),
        "delete": _("Message deletions")
    }

    def edit(self, before: discord.Message, after: discord.Message):
        if self.is_opt_disabled("edit"):
            return None
        if any([before.content == after.content, after.author.bot]):
            return

        embed = LogEntry(colour=discord.Colour.blurple())
        embed.set_author(name=_("Message Edited"), icon_url=self.icon_uri(after.author))
        embed.set_footer(text=_("Message ID: {}").format(after.id))
        embed.add_field(name=_("Message Author"), value=f"{after.author.mention} ({after.author.id})", inline=True)
        embed.add_field(name=_("Channel"), value=f"{after.channel.mention} ({after.channel.id})", inline=True)
        embed.add_differ_field(name=_("Content Diff"), before=before.content, after=after.content)

        return embed

    def delete(self, message: discord.Message):
        if self.is_opt_disabled("delete"):
            pass
        if message.author.bot:
            return

        embed = LogEntry(colour=discord.Colour.blurple())
        embed.set_author(name=_("Message Deleted"), icon_url=self.icon_uri(message.author))
        embed.set_footer(text=_("Message ID: {}").format(message.id))
        embed.add_field(name=_("Message Author"), value=f"{message.author.mention} ({message.author.id})", inline=True)
        embed.add_field(name=_("Channel"), value=f"{message.channel.mention} ({message.channel.id})", inline=True)
        embed.add_field(name=_("Content"), value=message.content or inline(_("No message content")))
        if message.attachments:
            embed.add_field(name=_("Attachments"), value="\n".join([f"<{x.url}>" for x in message.attachments]))

        return embed
