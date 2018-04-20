import discord

from logs.core import Module, LogEntry, _


class VoiceModule(Module):
    name = "voice"
    friendly_name = _("Voice")
    description = _("Voice status logging")
    settings = {
        "channel": _("Channel joining, leaving, and switching"),
        "mute": {
            "self": _("Self mute"),
            "server": _("Server mute"),
        },
        "deaf": {
            "self": _("Self deaf"),
            "server": _("Server deaf")
        }
    }

    async def update(self, before: discord.VoiceState, after: discord.VoiceState, member: discord.Member):
        embed = LogEntry(self, colour=discord.Colour.greyple())
        embed.set_author(name="Member Voice State Updated", icon_url=self.icon_uri(member))
        embed.description = _("Member: {}").format(member.mention)
        embed.set_footer(text=_("Member ID: {}").format(member.id))

        await embed.add_if_changed(name=_("Channel"), before=before.channel, after=after.channel,
                                   config_opt=('channel',))

        await embed.add_if_changed(name=_("Self Mute"), before=before.self_mute, after=after.self_mute,
                                   config_opt=('mute', 'self'))

        await embed.add_if_changed(name=_("Server Mute"), before=before.mute, after=after.mute,
                                   config_opt=('mute', 'server'))

        await embed.add_if_changed(name=_("Self Deaf"), before=before.self_deaf, after=after.self_deaf,
                                   config_opt=('deaf', 'self'))

        await embed.add_if_changed(name=_("Server Deaf"), before=before.deaf, after=after.deaf,
                                   config_opt=('deaf', 'server'))

        return embed
