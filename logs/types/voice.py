from datetime import datetime

import discord

from ._base import BaseLog
from logs.logentry import LogEntry


class VoiceLog(BaseLog):
    name = "voice"
    descriptions = {
        "channel": "Member voice channel joining, leaving, or switching",
        "selfmute": "Member self-mute",
        "selfdeaf": "Member self-deaf",
        "servermute": "Member server mute",
        "serverdeaf": "Member server deafen"
    }

    def update(self, before: discord.VoiceState, after: discord.VoiceState, **kwargs):
        try:
            member: discord.Member = kwargs["member"]
        except KeyError:  # Silently fail if the member in question wasn't given
            return None

        settings = self.settings
        ret = LogEntry(self, colour=discord.Colour.greyple())
        ret.set_title(title="Member Voice Status", icon_url=member.avatar_url_as(format="png"))
        ret.description = f"Member: {member.mention}"
        ret.set_footer(footer=f"User ID: {member.id}", timestamp=datetime.utcnow())

        if self.has_changed(before.channel, after.channel, "channel"):
            ret.add_diff_field(title="Voice Channel",
                               before=before.channel or "Not in voice",
                               after=after.channel or "Not in voice")

        if self.has_changed(before.self_deaf, after.self_deaf, "selfdeaf"):
            ret.add_field(title="Self Deaf",
                          value="{} self deafened".format("Now" if after.self_deaf else "No longer"))

        if self.has_changed(before.deaf, after.deaf, "serverdeaf"):
            ret.add_field(title="Server Deaf",
                          value="{} server deafened".format("Now" if after.deaf else "No longer"))

        if self.has_changed(before.self_mute, after.self_mute, "selfmute"):
            ret.add_field(title="Self Mute",
                          value="{} self muted".format("Now" if after.self_mute else "No longer"))

        if self.has_changed(before.mute, after.mute, "servermute"):
            ret.add_field(title="Server Mute",
                          value="{} server muted".format("Now" if after.mute else "No longer"))
        return ret

    def create(self, created, **kwargs):
        return NotImplemented

    def delete(self, deleted, **kwargs):
        return NotImplemented
