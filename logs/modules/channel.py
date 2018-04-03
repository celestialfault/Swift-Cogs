import discord

from logs.core import Module, LogEntry, _


class ChannelModule(Module):
    name = "channel"
    friendly_name = _("Channel")
    description = _("Channel creation, deletion, and update logging")
    settings = {
        "create": _("Channel creations"),
        "delete": _("Channel deletions"),
        "update": {
            "name": _("Channel name update"),
            "category": _("Channel category changes"),
            "position": _("Channel position changes"),
            "topic": _("Channel topic changes"),
            "bitrate": _("Channel bitrate changes"),
            "userlimit": _("Channel user limit changes")
        }
    }

    def create(self, channel: discord.abc.GuildChannel):
        return (
            LogEntry(colour=discord.Color.green(), require_fields=False,
                     description=_("Channel {} was created").format(channel.mention))
            .set_author(name=_("Channel Created"), icon_url=self.icon_uri())
            .set_footer(text=_("Channel ID: {}").format(channel.id))
        ) if self.is_opt_enabled("create") else None

    def delete(self, channel: discord.abc.GuildChannel):
        return (
            LogEntry(colour=discord.Color.red(), require_fields=False,
                     description=_("Channel `{}` was deleted").format(getattr(channel, "name", _("Unknown channel"))))
            .set_author(name=_("Channel Deleted"), icon_url=self.icon_uri())
            .set_footer(text=_("Channel ID: {}").format(channel.id))
        ) if self.is_opt_enabled("delete") else None

    def update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        embed = (
            LogEntry(colour=discord.Color.blurple(), description=_("Channel: {}").format(after.mention))
            .set_footer(text=_("Channel ID: {}").format(after.id))
            .set_author(name=_("Channel Updated"), icon_url=self.icon_uri())
        )

        # noinspection PyUnresolvedReferences
        if before.name != after.name and self.is_opt_enabled("update", "name"):
            # noinspection PyUnresolvedReferences
            embed.add_diff_field(name=_("Name"), before=before.name, after=after.name)

        if before.category != after.category and self.is_opt_enabled("update", "category"):
            embed.add_diff_field(name=_("Category"),
                                 before=getattr(before.category, "mention", _("None")),
                                 after=getattr(after.category, "mention", _("None")))

        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            if before.topic != after.topic and self.is_opt_enabled("update", "topic"):
                embed.add_differ_field(name=_("Channel Topic"), before=before.topic, after=after.topic)

        elif isinstance(before, discord.VoiceChannel) and isinstance(after, discord.VoiceChannel):
            if before.user_limit != after.user_limit and self.is_opt_enabled("update", "userlimit"):
                embed.add_diff_field(name=_("User Limit"), before=before.user_limit, after=after.user_limit)

            if before.bitrate != after.bitrate and self.is_opt_enabled("update", "bitrate"):
                # noinspection PyUnresolvedReferences
                embed.add_diff_field(name=_("Bitrate"),
                                     before=f"{str(before.bitrate)[:4]} kbps",
                                     after=f"{str(after.bitrate)[:4]} kbps")

        if before.position != after.position and self.is_opt_enabled("update", "position"):
            embed.add_diff_field(name=_("Channel Position"), before=before.position, after=after.position)

        return embed
