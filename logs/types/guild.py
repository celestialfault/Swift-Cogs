from datetime import timedelta, datetime

import discord
from redbot.core.utils.chat_formatting import escape

from .base import LogType
from logs.logentry import LogEntry
from logs.utils import normalize, td_format


class GuildLogType(LogType):
    name = "guild"

    async def update(self, before: discord.Guild, after: discord.Guild, **kwargs):
        if before.unavailable or after.unavailable:
            return None
        settings = await self.guild.config.guild()
        ret = LogEntry(self)
        ret.title = "Guild updated"
        ret.emoji = "\N{MEMO}"
        ret.timestamp = datetime.utcnow()
        ret.colour = discord.Colour.blurple()
        if before.name != after.name and settings["name"]:
            ret.add_diff_field(title="Name Changed",
                               before=escape(before.name, mass_mentions=True),
                               after=escape(after.name, mass_mentions=True))

        if before.verification_level != after.verification_level and settings["verification"]:
            ret.add_diff_field(title="Verification Level Changed",
                               before=normalize(str(before.verification_level), title_case=True),
                               after=normalize(str(after.verification_level), title_case=True))

        if before.explicit_content_filter != after.explicit_content_filter and settings["content_filter"]:
            ret.add_diff_field(title="Content Filter Changed",
                               before=normalize(str(before.explicit_content_filter), title_case=True),
                               after=normalize(str(after.explicit_content_filter), title_case=True))

        if before.owner_id != after.owner_id and settings["owner"]:
            ret.add_diff_field(title="Ownership Transferred",
                               before=str(before.owner),
                               after=str(after.owner))

        if before.mfa_level != after.mfa_level and settings["2fa"]:
            ret.add_diff_field(title="2FA Requirement",
                               before="Enabled" if before.mfa_level else "Disabled",
                               after="Enabled" if after.mfa_level else "Disabled")

        if before.afk_channel != after.afk_channel and settings["afk"]:
            ret.add_diff_field(title="AFK Channel Changed",
                               before=str(before.afk_channel or "No AFK channel"),
                               after=str(after.afk_channel or "No AFK channel"))

        if before.afk_timeout != after.afk_timeout and settings["afk"]:
            ret.add_diff_field(title="AFK Timeout Changed",
                               before=td_format(timedelta(seconds=before.afk_timeout)),
                               after=td_format(timedelta(seconds=after.afk_timeout)))

        if before.region != after.region and "region" in settings and settings["region"]:
            ret.add_diff_field(title="Voice Region Changed",
                               before=before.region,
                               after=after.region)
        return ret

    def create(self, created, **kwargs):
        raise NotImplementedError

    def delete(self, deleted, **kwargs):
        raise NotImplementedError
