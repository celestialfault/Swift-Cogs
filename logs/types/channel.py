from datetime import datetime

import discord

from logs.logentry import LogEntry
from ._base import BaseLogType, _


def format_userlimit(user_limit: int = None):
    if user_limit is None or user_limit == 0:
        return "No limit"
    if user_limit == 1:
        return "1 user"
    else:
        return f"{str(user_limit)} users"


class ChannelLogType(BaseLogType):
    name = "channels"
    descriptions = {
        "create": _("Channel creation"),
        "delete": _("Channel deletion"),
        "name": _("Channel name"),
        "topic": _("Text channel topics"),
        "category": _("Channel category"),
        "bitrate": _("Voice channel bitrate"),
        "user_limit": _("Voice channel user limit"),
        "position": _("Channel position changes")
    }

    def create(self, created: discord.abc.GuildChannel, **kwargs):
        if self.is_disabled('create'):
            return None

        return LogEntry(colour=discord.Colour.green(), title=_("Channel Created"), timestamp=datetime.utcnow(),
                        description=_("Channel {} created").format(created.mention), require_fields=False)\
            .set_footer(text=_("Channel ID: {}").format(created.id))

    async def update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel, **kwargs):
        embed = LogEntry(colour=discord.Colour.blurple(), timestamp=datetime.utcnow(),
                         description=_("Channel: {}").format(after.mention))
        embed.set_author(name=_("Channel Updated"), icon_url=self.guild_icon_url)
        # noinspection PyUnresolvedReferences
        embed.set_footer(text=_("Channel ID: {}").format(after.id))

        if hasattr(before, "name") and hasattr(after, "name"):  # you win this time pycharm
            if self.has_changed(before.name, after.name, "name"):
                embed.add_diff_field(name=_("Channel Name"), before=before.name, after=after.name)

        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            if self.has_changed(before.topic, after.topic, "topic"):
                embed.add_diff_field(name=_("Channel Topic"), before=before.topic, after=after.topic)

        elif isinstance(before, discord.VoiceChannel) and isinstance(after, discord.VoiceChannel):
            if self.has_changed(before.bitrate, after.bitrate, "bitrate"):
                # noinspection PyUnresolvedReferences
                embed.add_diff_field(name=_("Channel Bitrate"), before=f"{str(before.bitrate)[:-3]} kbps",
                                     after=f"{str(after.bitrate)[:-3]} kbps")

            if self.has_changed(before.user_limit, after.user_limit, "user_limit"):
                embed.add_diff_field(name=_("User Limit"), before=format_userlimit(before.user_limit),
                                     after=format_userlimit(after.user_limit))

        if self.has_changed(before.category, after.category, "category"):
            embed.add_diff_field(name=_("Channel Category"),
                                 before=getattr(before.category, "name", _("Uncategorized")),
                                 after=getattr(after.category, "name", _("Uncategorized")))

        if self.has_changed(before.position, after.position, "position"):
            embed.add_diff_field(name=_("Channel Position"), before=before.position, after=after.position)

        return embed

    def delete(self, deleted: discord.abc.GuildChannel, **kwargs):
        if not self.settings.get("delete", False):
            return None

        return LogEntry(colour=discord.Colour.red(), title=_("Channel Deleted"), timestamp=datetime.utcnow(),
                        description=_("Channel `{}` deleted").format(str(deleted)), require_fields=False)\
            .set_footer(text=_("Channel ID: {}").format(deleted.id))
