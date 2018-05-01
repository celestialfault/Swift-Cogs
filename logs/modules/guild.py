from datetime import timedelta

import discord

from logs.core import Module, LogEntry, i18n

from cog_shared.odinair_libs import normalize, td_format


class GuildModule(Module):
    name = "guild"
    friendly_name = i18n("Server")
    description = i18n("Server update logging")
    settings = {
        "2fa": i18n("Administration two-factor authentication requirement"),
        "afk": {
            "timeout": i18n("How long members can be AFK in voice"),
            "channel": i18n("The voice channel AFK members will be moved to"),
        },
        "name": i18n("Guild name"),
        "owner": i18n("Guild ownership transfers"),
        "region": i18n("Voice server region"),
        "filter": i18n("Explicit content filter"),
    }

    async def update(self, before: discord.Guild, after: discord.Guild):
        if any([before.unavailable, after.unavailable]):
            return None

        embed = LogEntry(self, colour=discord.Color.blurple())
        embed.set_author(name=i18n("Server Updated"), icon_url=self.icon_uri())
        embed.set_footer(text=i18n("Server ID: {}").format(after.id))

        await embed.add_if_changed(
            name=i18n("2FA Requirement"),
            before=before.mfa_level,
            after=after.mfa_level,
            converter=lambda x: i18n("Enabled") if x == 1 else i18n("Disabled"),
            config_opt=("2fa",),
        )

        await embed.add_if_changed(
            name=i18n("AFK Channel"),
            before=before.afk_channel,
            after=after.afk_channel,
            converter=lambda x: getattr(x, "mention", i18n("None")),
            config_opt=("afk", "channel"),
        )

        await embed.add_if_changed(
            name=i18n("AFK Timeout"),
            before=before.afk_timeout,
            after=after.afk_timeout,
            converter=lambda x: td_format(timedelta(seconds=x)),
            config_opt=("afk", "timeout"),
        )

        await embed.add_if_changed(
            name=i18n("Name"), before=before.name, after=after.name, config_opt=("name",)
        )

        await embed.add_if_changed(
            name=i18n("Owner"),
            before=before.owner,
            after=after.owner,
            converter=lambda x: getattr(x, "mention", str(x)),
            config_opt=("owner",),
        )

        await embed.add_if_changed(
            name=i18n("Voice Region"),
            before=before.region,
            after=after.region,
            config_opt=("region",),
        )

        await embed.add_if_changed(
            name=i18n("Content Filter"),
            converter=lambda x: normalize(x),
            config_opt=("filter",),
            before=before.explicit_content_filter,
            after=after.explicit_content_filter,
        )

        return embed
