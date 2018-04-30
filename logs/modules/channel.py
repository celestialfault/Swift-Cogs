import discord

from logs.core import Module, LogEntry, i18n


class ChannelModule(Module):
    name = "channel"
    friendly_name = i18n("Channel")
    description = i18n("Channel creation, deletion, and update logging")
    settings = {
        "create": i18n("Channel creations"),
        "delete": i18n("Channel deletions"),
        "update": {
            "name": i18n("Channel name update"),
            "category": i18n("Channel category changes"),
            "position": i18n("Channel position changes"),
            "topic": i18n("Channel topic changes"),
            "bitrate": i18n("Channel bitrate changes"),
            "userlimit": i18n("Channel user limit changes")
        }
    }

    async def create(self, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        return (
            LogEntry(self, colour=discord.Color.green(), require_fields=False,
                     description=i18n("Channel {} was created").format(channel.mention))
            .set_author(name=i18n("Channel Created"), icon_url=self.icon_uri())
            .set_footer(text=i18n("Channel ID: {}").format(channel.id))
        ) if await self.is_opt_enabled("create") else None

    async def delete(self, channel: discord.abc.GuildChannel):
        # noinspection PyUnresolvedReferences
        return (
            LogEntry(self, colour=discord.Color.red(), require_fields=False,
                     description=i18n("Channel `{}` was deleted").format(
                         getattr(channel, "name", i18n("Unknown channel"))))
            .set_author(name=i18n("Channel Deleted"), icon_url=self.icon_uri())
            .set_footer(text=i18n("Channel ID: {}").format(channel.id))
        ) if await self.is_opt_enabled("delete") else None

    async def update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        embed = LogEntry(self, colour=discord.Color.blurple(), description=i18n("Channel: {}").format(after.mention))
        # noinspection PyUnresolvedReferences
        embed.set_footer(text=i18n("Channel ID: {}").format(after.id))
        embed.set_author(name=i18n("Channel Updated"), icon_url=self.icon_uri())

        # noinspection PyUnresolvedReferences
        await embed.add_if_changed(name=i18n("Name"), before=before.name, after=after.name,
                                   config_opt=('update', 'name'))

        await embed.add_if_changed(name=i18n("Category"), before=before.category, after=after.category,
                                   converter=lambda x: getattr(x, "mention", i18n("None")),
                                   config_opt=('update', 'category'))

        await embed.add_if_changed(name=i18n("Position"), before=before.position, after=after.position,
                                   config_opt=('update', 'position'))

        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            await embed.add_if_changed(name=i18n("Channel Topic"), before=before.topic, after=after.topic, diff=True,
                                       config_opt=('update', 'topic'))

        elif isinstance(before, discord.VoiceChannel) and isinstance(after, discord.VoiceChannel):
            await embed.add_if_changed(name=i18n("User Limit"), before=before.user_limit, after=after.user_limit,
                                       config_opt=('update', 'userlimit'))

            await embed.add_if_changed(name=i18n("Bitrate"), before=before.bitrate, after=after.bitrate,
                                       converter=lambda x: "{} kbps".format(x[:4]),
                                       config_opt=('update', 'bitrate'))

        return embed
