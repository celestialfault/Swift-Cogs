import discord

from .base import LogType
from logs.logentry import LogEntry


class VoiceLogType(LogType):
    name = "voice"

    async def update(self, before: discord.VoiceState, after: discord.VoiceState, **kwargs):
        member = kwargs.get("member")
        settings = await self.guild.config.voice()
        ret = LogEntry(self, self.guild)
        ret.title = "Member {0!s} voice status updated".format(member)
        ret.icon_url = member.avatar_url
        ret.emoji = "\N{SPEAKER}"
        if before.channel != after.channel:
            if before.channel is not None and after.channel is not None:  # Channel switched
                if settings["switch"]:
                    ret.add_field(title="Voice channel", value="Switched to channel **{0!s}**".format(after.channel))
            elif before.channel is None and after.channel is not None:  # Channel joined
                if settings["join"]:
                    ret.add_field(title="Voice channel", value="Joined voice channel {0!s}".format(after.channel))
            elif before.channel is not None and after.channel is None:  # Channel left
                if settings["leave"]:
                    ret.add_field(title="Voice channel", value="Left voice channel {0!s}".format(before.channel))
        if (before.self_deaf != after.self_deaf) and settings["selfdeaf"]:
            ret.add_field(title="Deaf status", value="{} self deafened".format("Now" if after.self_deaf
                                                                               else "No longer"))
        if (before.self_mute != after.self_mute) and settings["selfmute"]:
            ret.add_field(title="Mute status", value="{} self muted".format("Now" if after.self_mute else "No longer"))
        if (before.deaf != after.deaf) and settings["serverdeaf"]:
            ret.add_field(title="Mute status", value="{} server deafened".format("Now" if after.deaf
                                                                                 else "No longer"))
        if (before.mute != after.mute) and settings["servermute"]:
            ret.add_field(title="Mute status", value="{} server muted".format("Now" if after.mute
                                                                              else "No longer"))
        return ret

    def create(self, created, **kwargs):
        raise NotImplementedError

    def delete(self, deleted, **kwargs):
        raise NotImplementedError
