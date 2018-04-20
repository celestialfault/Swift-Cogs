from datetime import timedelta

import discord

from logs.core import Module, LogEntry, _

from cog_shared.odinair_libs import normalize, td_format


class GuildModule(Module):
    name = "guild"
    friendly_name = _("Guild")
    description = _("Guild update logging")
    settings = {
        "2fa": _("Administration two-factor authentication requirement"),
        "afk": {
            "timeout": _("How long members can be AFK in voice"),
            "channel": _("The voice channel AFK members will be moved to"),
        },
        "name": _("Guild name"),
        "owner": _("Guild ownership transfers"),
        "region": _("Voice server region"),
        "filter": _("Explicit content filter")
    }

    async def update(self, before: discord.Guild, after: discord.Guild):
        if any([before.unavailable, after.unavailable]):
            return None

        embed = LogEntry(self, colour=discord.Color.blurple())
        embed.set_author(name=_("Guild Updated"), icon_url=self.icon_uri())
        embed.set_footer(text=_("Guild ID: {}").format(after.id))

        await embed.add_if_changed(name=_("2FA Requirement"), before=before.mfa_level, after=after.mfa_level,
                                   converter=lambda x: _("Enabled") if x == 1 else _("Disabled"),
                                   config_opt=('2fa',))

        await embed.add_if_changed(name=_("AFK Channel"), before=before.afk_channel, after=after.afk_channel,
                                   converter=lambda x: getattr(x, "mention", _("None")),
                                   config_opt=('afk', 'channel'))

        await embed.add_if_changed(name=_("AFK Timeout"), before=before.afk_timeout, after=after.afk_timeout,
                                   converter=lambda x: td_format(timedelta(seconds=x)), config_opt=('afk', 'timeout'))

        await embed.add_if_changed(name=_("Name"), before=before.name, after=after.name, config_opt=('name',))

        await embed.add_if_changed(name=_("Owner"), before=before.owner, after=after.owner,
                                   converter=lambda x: getattr(x, "mention", str(x)), config_opt=('owner',))

        await embed.add_if_changed(name=_("Voice Region"), before=before.region, after=after.region,
                                   config_opt=('region',))

        await embed.add_if_changed(name=_("Content Filter"), converter=lambda x: normalize(x), config_opt=('filter',),
                                   before=before.explicit_content_filter,
                                   after=after.explicit_content_filter)

        return embed
