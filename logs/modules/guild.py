from datetime import timedelta

import discord

from logs.core import Module, LogEntry, _

from cog_shared.odinair_libs.formatting import td_format, normalize


class GuildModule(Module):
    name = "guild"
    friendly_name = _("Guild")
    module_description = _("Guild update logging")
    defaults = {
        "2fa": False,
        "afk": {
            "timeout": False,
            "channel": None
        },
        "name": False,
        "owner": False,
        "region": False,
        "filter": False
    }
    option_descriptions = {
        "2fa": _("Administration two-factor authentication requirement"),
        "afk:timeout": _("How long members can be AFK in voice"),
        "afk:channel": _("The voice channel AFK members will be moved to"),
        "name": _("Guild name"),
        "owner": _("Guild ownership transfers"),
        "region": _("Voice server region"),
        "filter": _("Explicit content filter")
    }

    def update(self, before: discord.Guild, after: discord.Guild):
        if any([before.unavailable, after.unavailable]):
            return None

        embed = LogEntry(colour=discord.Colour.blurple())
        embed.set_author(name=_("Guild Updated"), icon_url=self.icon_uri())
        embed.set_footer(text=_("Guild ID: {}").format(after.id))

        if before.mfa_level != after.mfa_level and self.is_opt_enabled("2fa"):
            embed.add_diff_field(name=_("2FA Requirement"), before=_("Enabled") if before.mfa_level else _("Disabled"),
                                 after=_("Enabled") if after.mfa_level else _("Disabled"))

        if before.afk_channel != after.afk_channel and self.is_opt_enabled("afk", "channel"):
            embed.add_diff_field(name=_("AFK Channel"),
                                 before=getattr(before.afk_channel, "mention", _("None")),
                                 after=getattr(before.afk_channel, "mention", _("None")))

        if before.afk_timeout != after.afk_timeout and self.is_opt_enabled("afk", "timeout"):
            embed.add_diff_field(name=_("AFK Timeout"),
                                 before=td_format(timedelta(seconds=before.afk_timeout)),
                                 after=td_format(timedelta(seconds=after.afk_timeout)))

        if before.name != after.name and self.is_opt_enabled("name"):
            embed.add_diff_field(name=_("Guild Name"), before=before.name, after=after.name)

        if before.owner != after.owner and self.is_opt_enabled("owner"):
            embed.add_diff_field(name=_("Guild Owner"),
                                 before=getattr(before.owner, "mention", str(before.owner)),
                                 after=getattr(after.owner, "mention", str(after.owner)))

        if before.region != after.region and self.is_opt_enabled("region"):
            embed.add_diff_field(name=_("Voice Region"), before=str(before.region), after=str(after.region))

        if before.explicit_content_filter != after.explicit_content_filter and self.is_opt_enabled("filter"):
            embed.add_diff_field(name=_("Content Filter"),
                                 before=normalize(before.explicit_content_filter),
                                 after=normalize(after.explicit_content_filter))

        return embed
