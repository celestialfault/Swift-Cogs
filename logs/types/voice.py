from datetime import datetime

import discord

from logs.logentry import LogEntry
from ._base import BaseLog


class VoiceLog(BaseLog):
    name = "voice"
    descriptions = {
        "channel": "Member voice channel joining, leaving, or switching",
        "selfmute": "Member self-mute",
        "selfdeaf": "Member self-deaf",
        "servermute": "Member server mute",
        "serverdeaf": "Member server deafen"
    }

    def create(self, **kwargs):
        return NotImplemented

    def update(self, before: discord.VoiceState, after: discord.VoiceState, **kwargs):
        try:
            member: discord.Member = kwargs["member"]
        except KeyError:  # Silently fail if the member in question wasn't given
            return None

        embed = LogEntry(colour=discord.Colour.greyple(), description=f"Member: {member.mention}",
                         timestamp=datetime.utcnow())
        embed.set_author(name="Member Voice Status", icon_url=member.avatar_url_as(format="png"))
        embed.set_footer(text=f"User ID: {member.id}")

        if self.has_changed(before.channel, after.channel, "channel"):
            embed.add_diff_field(name="Voice Channel", before=before.channel, after=after.channel)

        if self.has_changed(before.self_deaf, after.self_deaf, "selfdeaf"):
            status = "Now" if after.self_deaf else "No longer"
            embed.add_field(name="Self Deaf", value=f"{status} self deafened")

        if self.has_changed(before.deaf, after.deaf, "serverdeaf"):
            status = "Now" if after.deaf else "No longer"
            embed.add_field(name="Server Deaf", value=f"{status} server deafened")

        if self.has_changed(before.self_mute, after.self_mute, "selfmute"):
            status = "Now" if after.self_mute else "No longer"
            embed.add_field(name="Self Mute", value=f"{status} self muted")

        if self.has_changed(before.mute, after.mute, "servermute"):
            status = "Now" if after.mute else "No longer"
            embed.add_field(name="Server Mute", value=f"{status} server muted")

        return embed

    def delete(self, **kwargs):
        return NotImplemented
