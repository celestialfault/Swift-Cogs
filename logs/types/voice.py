from datetime import datetime

import discord

from .base import LogType
from logs.logentry import LogEntry


class VoiceLogType(LogType):
    name = "voice"

    async def update(self, before: discord.VoiceState, after: discord.VoiceState, **kwargs):
        try:
            member = kwargs["member"]
        except KeyError:  # Silently fail if the member in question wasn't given
            return None

        settings = await self.guild.config.voice()
        ret = LogEntry(self, colour=discord.Colour.greyple())
        ret.set_title(title="Voice status updated", icon_url=member.avatar_url, emoji="\N{SPEAKER}")
        ret.set_footer(footer="User ID: {0.id}".format(member), timestamp=datetime.utcnow())
        ret.description = "Member: **{0!s}**".format(member)

        if before.channel != after.channel and settings.get("channel", False):
            ret.add_diff_field(title="Voice Channel",
                               before=before.channel or "Not in voice",
                               after=after.channel or "Not in voice")

        if before.self_deaf != after.self_deaf and settings.get("selfdeaf", False):
            ret.add_field(title="Self Deaf",
                          value="{} self deafened".format("Now" if after.self_deaf else "No longer"))

        if before.deaf != after.deaf and settings.get("serverdeaf", False):
            ret.add_field(title="Server Deaf",
                          value="{} server deafened".format("Now" if after.deaf else "No longer"))

        if before.self_mute != after.self_mute and settings.get("selfmute", False):
            ret.add_field(title="Self Mute",
                          value="{} self muted".format("Now" if after.self_mute else "No longer"))

        if before.mute != after.mute and settings.get("servermute", False):
            ret.add_field(title="Server Mute",
                          value="{} server muted".format("Now" if after.mute else "No longer"))
        return ret

    def create(self, created, **kwargs):
        raise NotImplementedError

    def delete(self, deleted, **kwargs):
        raise NotImplementedError
