from datetime import timedelta

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
        ret.colour = discord.Colour.blurple()
        if before.name != after.name and settings["name"]:
            name = escape(after.name, mass_mentions=True)
            ret.add_field(title="Guild Name", value="Guild name changed to {}".format(name))
        if before.verification_level != after.verification_level and settings["verification"]:
            lvl = normalize(str(after.verification_level), title_case=True)
            ret.add_field(title="Verification Level", value="Guild verification level now set to {}".format(
                lvl))
        if before.explicit_content_filter != after.explicit_content_filter and settings["content_filter"]:
            lvl = normalize(str(after.explicit_content_filter), title_case=True)
            ret.add_field(title="Content Filter", value="Guild content filter set to {}".format(lvl))
        if before.owner_id != after.owner_id and settings["owner"]:
            ret.add_field(title="Guild Ownership", value="Guild ownership transferred to {0!s} ({0.id})".format(
                after.owner))
        if before.mfa_level != after.mfa_level and settings["2fa"]:
            ret.add_field(title="2FA Requirement", value="Guild {} requires 2FA for administrative permissions".format(
                "now" if after.mfa_level == 1 else "no longer"))
        if before.afk_channel != after.afk_channel and settings["afk"]:
            if after.afk_channel:
                ret.add_field(title="AFK Channel", value="AFK channel set to {0!s}".format(after.afk_channel))
            else:
                ret.add_field(title="AFK Channel", value="AFK channel unset")
        if before.afk_timeout != after.afk_timeout and settings["afk"]:
            delta = timedelta(seconds=after.afk_timeout)
            ret.add_field(title="AFK Timeout", value="AFK timeout set to {0}".format(td_format(delta)))
        if before.region != after.region and "region" in settings and settings["region"]:
            ret.add_field(title="Guild Region", value="Guild voice region set to {0}".format(after.region))
        return ret

    def create(self, created, **kwargs):
        raise NotImplementedError

    def delete(self, deleted, **kwargs):
        raise NotImplementedError
