from datetime import timedelta, datetime

import discord

from logs.logentry import LogEntry
from ._base import BaseLogType, _

from odinair_libs.formatting import td_format, normalize


class ServerLogType(BaseLogType):
    name = "server"
    descriptions = {
        "2fa": _("Two-factor authentication requirement"),
        "verification": _("Member verification level"),
        "name": _("Guild name"),
        "owner": _("Ownership changes"),
        "afk": _("AFK channel and timeout"),
        "region": _("Voice region"),
        "content_filter": _("Explicit content filter")
    }

    def create(self, **kwargs):
        return NotImplemented

    async def update(self, before: discord.Guild, after: discord.Guild, **kwargs):
        if before.unavailable or after.unavailable:
            # Ignore unavailable guilds, as we have no promise of the accuracy of any data
            return None

        embed = LogEntry(colour=discord.Colour.blurple(), timestamp=datetime.utcnow())
        embed.set_author(name=_("Server Updated"), icon_url=self.guild_icon_url)
        embed.set_footer(text=_("Server ID: {}").format(after.id))

        if self.has_changed(before.name, after.name, "name"):
            embed.add_diff_field(name=_("Server Name"), before=before.name, after=after.name)

        if self.has_changed(before.verification_level, after.verification_level, "verification"):
            embed.add_diff_field(name=_("Verification Level"), before=normalize(str(before.verification_level)),
                                 after=normalize(str(after.verification_level)))

        if self.has_changed(before.explicit_content_filter, after.explicit_content_filter, "content_filter"):
            embed.add_diff_field(name=_("Content Filter"), before=normalize(str(before.explicit_content_filter)),
                                 after=normalize(str(after.explicit_content_filter)))

        if self.has_changed(before.owner, after.owner, "owner"):
            embed.add_diff_field(name=_("Server Owner"), before=before.owner.mention, after=after.owner.mention)

        if self.has_changed(before.mfa_level, after.mfa_level, "2fa"):
            embed.add_diff_field(name=_("2FA Requirement"), before=_("Enabled") if before.mfa_level else _("Disabled"),
                                 after=_("Enabled") if after.mfa_level else _("Disabled"))

        if self.has_changed(before.afk_channel, after.afk_channel, "afk"):
            embed.add_diff_field(name=_("AFK Channel"), before=before.afk_channel, after=after.afk_channel)

        if self.has_changed(before.afk_timeout, after.afk_timeout, "afk"):
            embed.add_diff_field(name=_("AFK Timeout"), before=td_format(timedelta(seconds=before.afk_timeout)),
                                 after=td_format(timedelta(seconds=after.afk_timeout)))

        if self.has_changed(before.region, after.region, "region"):
            embed.add_diff_field(name=_("Voice Region"), before=before.region, after=after.region)

        return embed

    def delete(self, **kwargs):
        return NotImplemented
