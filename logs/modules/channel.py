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

    async def create(self, channel: discord.abc.GuildChannel):
        return (
            LogEntry(colour=discord.Color.green(), require_fields=False,
                     description=_("Channel {} was created").format(channel.mention))
            .set_author(name=_("Channel Created"), icon_url=self.icon_uri())
            .set_footer(text=_("Channel ID: {}").format(channel.id))
        ) if await self.is_opt_enabled("create") else None

    async def delete(self, channel: discord.abc.GuildChannel):
        return (
            LogEntry(colour=discord.Color.red(), require_fields=False,
                     description=_("Channel `{}` was deleted").format(
                         getattr(channel, "name", _("Unknown channel"))))
            .set_author(name=_("Channel Deleted"), icon_url=self.icon_uri())
            .set_footer(text=_("Channel ID: {}").format(channel.id))
        ) if await self.is_opt_enabled("delete") else None

    async def update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        embed = (
            LogEntry(colour=discord.Color.blurple(), description=_("Channel: {}").format(after.mention))
            .set_footer(text=_("Channel ID: {}").format(after.id))
            .set_author(name=_("Channel Updated"), icon_url=self.icon_uri())
        )

        # noinspection PyUnresolvedReferences
        if before.name != after.name and await self.is_opt_enabled("update", "name"):
            # noinspection PyUnresolvedReferences
            embed.add_diff_field(name=_("Name"), before=before.name, after=after.name)

        if before.category != after.category and await self.is_opt_enabled("update", "category"):
            embed.add_diff_field(name=_("Category"),
                                 before=getattr(before.category, "mention", _("None")),
                                 after=getattr(after.category, "mention", _("None")))

        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            if before.topic != after.topic and await self.is_opt_enabled("update", "topic"):
                embed.add_differ_field(name=_("Channel Topic"), before=before.topic, after=after.topic)

        elif isinstance(before, discord.VoiceChannel) and isinstance(after, discord.VoiceChannel):
            if before.user_limit != after.user_limit and await self.is_opt_enabled("update", "userlimit"):
                embed.add_diff_field(name=_("User Limit"), before=before.user_limit, after=after.user_limit)

            if before.bitrate != after.bitrate and await self.is_opt_enabled("update", "bitrate"):
                # noinspection PyUnresolvedReferences
                embed.add_diff_field(name=_("Bitrate"),
                                     before=str(before.bitrate)[:4] + " kbps",
                                     after=str(after.bitrate)[:4] + " kbps")

        if before.position != after.position and await self.is_opt_enabled("update", "position"):
            embed.add_diff_field(name=_("Channel Position"), before=before.position, after=after.position)

        return embed
