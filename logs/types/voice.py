from datetime import datetime

import discord

from logs.logentry import LogEntry
from ._base import BaseLogType, _


class VoiceLogType(BaseLogType):
    name = "voice"
    descriptions = {
        "channel": _("Member voice channel joining, leaving, or switching"),
        "selfmute": _("Member self-mute"),
        "selfdeaf": _("Member self-deaf"),
        "servermute": _("Member server mute"),
        "serverdeaf": _("Member server deafen")
    }

    def create(self, **kwargs):
        return NotImplemented

    def update(self, before: discord.VoiceState, after: discord.VoiceState, **kwargs):
        try:
            member: discord.Member = kwargs["member"]
        except KeyError:  # Silently fail if the member in question wasn't given
            return None

        embed = LogEntry(colour=discord.Colour.greyple(), description=_("Member: {}").format(member.mention),
                         timestamp=datetime.utcnow())
        embed.set_author(name=_("Member Voice Status"), icon_url=self.icon_url(member))
        embed.set_footer(text=_("User ID: {}").format(member.id))

        if self.has_changed(before.channel, after.channel, "channel"):
            embed.add_diff_field(name=_("Voice Channel"), before=before.channel, after=after.channel)

        if self.has_changed(before.self_deaf, after.self_deaf, "selfdeaf"):
            if after.self_deaf:
                status = _("Now self deafened")
            else:
                status = _("No longer self deafened")
            embed.add_field(name=_("Self Deaf"), value=status)

        if self.has_changed(before.deaf, after.deaf, "serverdeaf"):
            if after.deaf:
                status = _("Now server deafened")
            else:
                status = _("No longer server deafened")
            embed.add_field(name=_("Server Deaf"), value=status)

        if self.has_changed(before.self_mute, after.self_mute, "selfmute"):
            if after.self_mute:
                status = _("Now self muted")
            else:
                status = _("No longer self muted")
            embed.add_field(name=_("Self Mute"), value=status)

        if self.has_changed(before.mute, after.mute, "servermute"):
            if after.mute:
                status = _("Now server muted")
            else:
                status = _("No longer server muted")
            embed.add_field(name=_("Server Mute"), value=status)

        return embed

    def delete(self, **kwargs):
        return NotImplemented
