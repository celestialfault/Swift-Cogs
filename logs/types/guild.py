from datetime import timedelta, datetime

import discord

from logs.logentry import LogEntry
from ._base import BaseLog

from odinair_libs.formatting import td_format, normalize


class GuildLog(BaseLog):
    name = "guild"
    descriptions = {
        "2fa": "Two-factor authentication requirement",
        "verification": "Member verification level",
        "name": "Guild name",
        "owner": "Ownership changes",
        "afk": "AFK channel and timeout",
        "region": "Voice region",
        "content_filter": "Explicit content filter"
    }

    def create(self, **kwargs):
        return NotImplemented

    async def update(self, before: discord.Guild, after: discord.Guild, **kwargs):
        if before.unavailable or after.unavailable:
            # Ignore unavailable guilds, as we have no promise of the accuracy of any data
            return None

        embed = LogEntry(colour=discord.Colour.blurple(), timestamp=datetime.utcnow())
        embed.set_author(name="Guild Updated", icon_url=self.guild_icon_url)
        embed.set_footer(text=f"Guild ID: {after.id}")

        if self.has_changed(before.name, after.name, "name"):
            embed.add_diff_field(name="Guild Name", before=before.name, after=after.name)

        if self.has_changed(before.verification_level, after.verification_level, "verification"):
            embed.add_diff_field(name="Verification Level", before=normalize(str(before.verification_level)),
                                 after=normalize(str(after.verification_level)))

        if self.has_changed(before.explicit_content_filter, after.explicit_content_filter, "content_filter"):
            embed.add_diff_field(name="Content Filter", before=normalize(str(before.explicit_content_filter)),
                                 after=normalize(str(after.explicit_content_filter)))

        if self.has_changed(before.owner, after.owner, "owner"):
            embed.add_diff_field(name="Guild Owner", before=before.owner.mention, after=after.owner.mention)

        if self.has_changed(before.mfa_level, after.mfa_level, "2fa"):
            embed.add_diff_field(name="2FA Requirement", before="Enabled" if before.mfa_level else "Disabled",
                                 after="Enabled" if after.mfa_level else "Disabled")

        if self.has_changed(before.afk_channel, after.afk_channel, "afk"):
            embed.add_diff_field(name="AFK Channel", before=before.afk_channel, after=after.afk_channel)

        if self.has_changed(before.afk_timeout, after.afk_timeout, "afk"):
            embed.add_diff_field(name="AFK Timeout", before=td_format(timedelta(seconds=before.afk_timeout)),
                                 after=td_format(timedelta(seconds=after.afk_timeout)))

        if self.has_changed(before.region, after.region, "region"):
            embed.add_diff_field(name="Voice Region", before=before.region, after=after.region)

        return embed

    def delete(self, **kwargs):
        return NotImplemented
