from datetime import timedelta, datetime

import discord
from redbot.core.utils.chat_formatting import escape

from ._base import BaseLog
from logs.logentry import LogEntry
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

    async def update(self, before: discord.Guild, after: discord.Guild, **kwargs):
        if before.unavailable or after.unavailable:
            # Ignore unavailable guilds, as we have no promise of the accuracy of any data
            return None

        settings = await self.guild.config.guild()
        ret = LogEntry(self, colour=discord.Colour.blurple())
        ret.set_title(title="Guild Updated")
        ret.set_footer(footer="Guild ID: {0.id}".format(after), timestamp=datetime.utcnow())

        if self.has_changed(before.name, after.name, "name"):
            ret.add_diff_field(title="Guild Name",
                               before=escape(before.name, mass_mentions=True),
                               after=escape(after.name, mass_mentions=True))

        if self.has_changed(before.verification_level, after.verification_level, "verification"):
            ret.add_diff_field(title="Verification Level",
                               before=normalize(str(before.verification_level), title_case=True),
                               after=normalize(str(after.verification_level), title_case=True))

        if self.has_changed(before.explicit_content_filter, after.explicit_content_filter, "content_filter"):
            ret.add_diff_field(title="Content Filter",
                               before=normalize(str(before.explicit_content_filter), title_case=True),
                               after=normalize(str(after.explicit_content_filter), title_case=True))

        if self.has_changed(before.owner, after.owner, "owner"):
            ret.add_diff_field(title="Guild Owner",
                               before=str(before.owner),
                               after=str(after.owner))

        if self.has_changed(before.mfa_level, after.mfa_level, "2fa"):
            ret.add_diff_field(title="2FA Requirement",
                               before="Enabled" if before.mfa_level else "Disabled",
                               after="Enabled" if after.mfa_level else "Disabled")

        if self.has_changed(before.afk_channel, after.afk_channel, "afk"):
            ret.add_diff_field(title="AFK Channel",
                               before=str(before.afk_channel or "No AFK channel"),
                               after=str(after.afk_channel or "No AFK channel"))

        if self.has_changed(before.afk_timeout, after.afk_timeout, "afk"):
            ret.add_diff_field(title="AFK Timeout",
                               before=td_format(timedelta(seconds=before.afk_timeout)),
                               after=td_format(timedelta(seconds=after.afk_timeout)))

        if self.has_changed(before.region, after.region, "region"):
            ret.add_diff_field(title="Voice Region",
                               before=before.region,
                               after=after.region)
        return ret

    def create(self, created, **kwargs):
        return NotImplemented

    def delete(self, deleted, **kwargs):
        return NotImplemented
