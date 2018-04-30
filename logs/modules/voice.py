import discord

from logs.core import Module, LogEntry, i18n


class VoiceModule(Module):
    name = "voice"
    friendly_name = i18n("Voice")
    description = i18n("Voice status logging")
    settings = {
        "channel": i18n("Channel joining, leaving, and switching"),
        "mute": {
            "self": i18n("Self mute"),
            "server": i18n("Server mute"),
        },
        "deaf": {
            "self": i18n("Self deaf"),
            "server": i18n("Server deaf")
        }
    }

    async def update(self, before: discord.VoiceState, after: discord.VoiceState, member: discord.Member):
        embed = LogEntry(self, colour=discord.Colour.greyple())
        embed.set_author(name="Member Voice State Updated", icon_url=self.icon_uri(member))
        embed.description = i18n("Member: {}").format(member.mention)
        embed.set_footer(text=i18n("Member ID: {}").format(member.id))

        await embed.add_if_changed(name=i18n("Channel"), before=before.channel, after=after.channel,
                                   config_opt=('channel',))

        await embed.add_if_changed(name=i18n("Self Mute"), before=before.self_mute, after=after.self_mute,
                                   config_opt=('mute', 'self'))

        await embed.add_if_changed(name=i18n("Server Mute"), before=before.mute, after=after.mute,
                                   config_opt=('mute', 'server'))

        await embed.add_if_changed(name=i18n("Self Deaf"), before=before.self_deaf, after=after.self_deaf,
                                   config_opt=('deaf', 'self'))

        await embed.add_if_changed(name=i18n("Server Deaf"), before=before.deaf, after=after.deaf,
                                   config_opt=('deaf', 'server'))

        return embed
