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
            LogEntry(self, colour=discord.Color.green(), require_fields=False,
                     description=_("Channel {} was created").format(channel.mention))
            .set_author(name=_("Channel Created"), icon_url=self.icon_uri())
            .set_footer(text=_("Channel ID: {}").format(channel.id))
        ) if await self.is_opt_enabled("create") else None

    async def delete(self, channel: discord.abc.GuildChannel):
        return (
            LogEntry(self, colour=discord.Color.red(), require_fields=False,
                     description=_("Channel `{}` was deleted").format(
                         getattr(channel, "name", _("Unknown channel"))))
            .set_author(name=_("Channel Deleted"), icon_url=self.icon_uri())
            .set_footer(text=_("Channel ID: {}").format(channel.id))
        ) if await self.is_opt_enabled("delete") else None

    async def update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        embed = LogEntry(self, colour=discord.Color.blurple(), description=_("Channel: {}").format(after.mention))
        embed.set_footer(text=_("Channel ID: {}").format(after.id))
        embed.set_author(name=_("Channel Updated"), icon_url=self.icon_uri())

        # noinspection PyUnresolvedReferences
        await embed.add_if_changed(name=_("Name"), before=before.name, after=after.name, config_opt=('update', 'name'))

        await embed.add_if_changed(name=_("Category"), before=before.category, after=after.category,
                                   converter=lambda x: getattr(x, "mention", _("None")),
                                   config_opt=('update', 'category'))

        await embed.add_if_changed(name=_("Position"), before=before.position, after=after.position,
                                   config_opt=('update', 'position'))

        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            await embed.add_if_changed(name=_("Channel Topic"), before=before.topic, after=after.topic, diff=True,
                                       config_opt=('update', 'topic'))

        elif isinstance(before, discord.VoiceChannel) and isinstance(after, discord.VoiceChannel):
            await embed.add_if_changed(name=_("User Limit"), before=before.user_limit, after=after.user_limit,
                                       config_opt=('update', 'userlimit'))

            await embed.add_if_changed(name=_("Bitrate"), before=before.bitrate, after=after.bitrate,
                                       converter=lambda x: "{} kbps".format(x[:4]),
                                       config_opt=('update', 'bitrate'))

        return embed
