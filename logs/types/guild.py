from datetime import timedelta, datetime

import discord
from redbot.core.utils.chat_formatting import escape

from .base import LogType
from logs.logentry import LogEntry
from odinair_libs.formatting import td_format, normalize


class GuildLogType(LogType):
    name = "guild"

    async def update(self, before: discord.Guild, after: discord.Guild, **kwargs):
        if before.unavailable or after.unavailable:
            # Ignore unavailable guilds, as we have no promise of the accuracy of any data
            return None

        settings = await self.guild.config.guild()
        ret = LogEntry(self, colour=discord.Colour.blurple())
        ret.set_title(title="Guild updated", emoji="\N{MEMO}")
        ret.set_footer(footer="Guild ID: {0.id}".format(after), timestamp=datetime.utcnow())

        if before.name != after.name and settings.get("name", False):
            ret.add_diff_field(title="Guild Name",
                               before=escape(before.name, mass_mentions=True),
                               after=escape(after.name, mass_mentions=True))

        if before.verification_level != after.verification_level and settings.get("verification", False):
            ret.add_diff_field(title="Verification Level",
                               before=normalize(str(before.verification_level), title_case=True),
                               after=normalize(str(after.verification_level), title_case=True))

        if before.explicit_content_filter != after.explicit_content_filter and settings.get("content_filter", False):
            ret.add_diff_field(title="Content Filter",
                               before=normalize(str(before.explicit_content_filter), title_case=True),
                               after=normalize(str(after.explicit_content_filter), title_case=True))

        if before.owner_id != after.owner_id and settings.get("owner", False):
            ret.add_diff_field(title="Guild Owner",
                               before=str(before.owner),
                               after=str(after.owner))

        if before.mfa_level != after.mfa_level and settings.get("2fa", False):
            ret.add_diff_field(title="2FA Requirement",
                               before="Enabled" if before.mfa_level else "Disabled",
                               after="Enabled" if after.mfa_level else "Disabled")

        if before.afk_channel != after.afk_channel and settings.get("afk", False):
            ret.add_diff_field(title="AFK Channel",
                               before=str(before.afk_channel or "No AFK channel"),
                               after=str(after.afk_channel or "No AFK channel"))

        if before.afk_timeout != after.afk_timeout and settings.get("afk", False):
            ret.add_diff_field(title="AFK Timeout",
                               before=td_format(timedelta(seconds=before.afk_timeout)),
                               after=td_format(timedelta(seconds=after.afk_timeout)))

        if before.region != after.region and settings.get("region", False):
            ret.add_diff_field(title="Voice Region",
                               before=before.region,
                               after=after.region)
        return ret

    def create(self, created, **kwargs):
        raise NotImplementedError

    def delete(self, deleted, **kwargs):
        raise NotImplementedError
