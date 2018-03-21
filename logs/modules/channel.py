import discord

from logs.core import Module, LogEntry, _


class ChannelModule(Module):
    name = "channel"
    friendly_name = _("Channel")
    module_description = _("Channel creation, deletion, and update logging")
    defaults = {
        "create": False,
        "delete": False,
        "update": {
            "name": False,
            "category": False,
            "position": False,
            "topic": False,
            "bitrate": False,
            "userlimit": False
        }
    }
    option_descriptions = {
        "create": _("Channel creations"),
        "delete": _("Channel deletions"),
        "update:name": _("Channel name update"),
        "update:category": _("Channel category changes"),
        "update:position": _("Channel position changes"),
        "update:topic": _("Channel topic changes"),
        "update:bitrate": _("Channel bitrate changes"),
        "update:userlimit": _("Channel user limit changes")
    }

    def create(self, channel: discord.abc.GuildChannel):
        if self.is_opt_disabled("create"):
            return None

        embed = LogEntry(colour=discord.Colour.green(), require_fields=False)
        embed.set_footer(text=_("Channel ID: {}").format(channel.id))
        embed.set_author(name=_("Channel Created"), icon_url=self.icon_uri())
        embed.description = _("Channel {} was created").format(channel.mention)
        return embed

    def delete(self, channel: discord.abc.GuildChannel):
        if self.is_opt_disabled("delete"):
            return None

        embed = LogEntry(colour=discord.Colour.red(), require_fields=False)
        embed.set_footer(text=_("Channel ID: {}").format(channel.id))
        embed.set_author(name=_("Channel Deleted"), icon_url=self.icon_uri())
        # noinspection PyUnresolvedReferences
        embed.description = _("Channel `{}` was deleted").format(channel.name)
        return embed

    def update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        embed = LogEntry(colour=discord.Colour.blurple())
        embed.set_footer(text=_("Channel ID: {}").format(after.id))
        embed.set_author(name=_("Channel Updated"), icon_url=self.icon_uri())

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
