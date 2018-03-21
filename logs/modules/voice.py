import discord

from logs.core import Module, LogEntry, _


class VoiceModule(Module):
    name = "voice"
    friendly_name = _("Voice")
    module_description = _("Voice status logging")
    defaults = {
        "channel": False,
        "mute": {
            "server": False,
            "self": False
        },
        "deaf": {
            "server": False,
            "self": False
        }
    }
    option_descriptions = {
        "channel": "Channel joining, leaving, and switching",
        "mute:self": "Self mute",
        "mute:server": "Server mute",
        "deaf:self": "Self deaf",
        "deaf:server": "Server deaf",
    }

    def update(self, before: discord.VoiceState, after: discord.VoiceState, member: discord.Member):
        embed = LogEntry(colour=discord.Colour.greyple())
        embed.set_author(name="Member Voice State Updated", icon_url=self.icon_uri(member))
        embed.description = _("Member: {}").format(member.mention)
        embed.set_footer(text=_("Member ID: {}").format(member.id))

        if before.channel != after.channel and self.is_opt_enabled("channel"):
            embed.add_diff_field(name=_("Channel Changed"), before=str(before.channel), after=str(after.channel))

        if before.self_mute != after.self_mute and self.is_opt_enabled("mute", "self"):
            embed.add_diff_field(name=_("Self Mute Status"), before=str(before.self_mute), after=str(after.self_mute))

        if before.mute != after.mute and self.is_opt_enabled("mute", "server"):
            embed.add_diff_field(name=_("Server Mute Status"), before=str(before.mute), after=str(after.mute))

        if before.self_deaf != after.self_deaf and self.is_opt_enabled("deaf", "self"):
            embed.add_diff_field(name=_("Self Deaf Status"), before=str(before.self_deaf), after=str(after.self_deaf))

        if before.deaf != after.deaf and self.is_opt_enabled("deaf", "server"):
            embed.add_diff_field(name=_("Server Deaf Status"), before=str(before.deaf), after=str(after.deaf))

        return embed
