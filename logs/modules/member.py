from datetime import datetime

import discord

from logs.core import Module, LogEntry, _

from cog_shared.odinair_libs.formatting import td_format


class MemberModule(Module):
    friendly_name = _("Member")
    name = "member"
    module_description = _("Member joining, leaving, and update logging")
    defaults = {
        "join": False,
        "leave": False,
        "update": {
            "name": False,
            "discriminator": False,
            "nickname": False,
            "roles": False
        }
    }
    option_descriptions = {
        "join": _("Member joining"),
        "leave": _("Member leaving"),
        "update:name": _("Member username changes"),
        "update:discriminator": _("Member discriminator changes"),
        "update:nickname": _("Member nickname changes"),
        "update:roles": _("Member role changes")
    }

    def join(self, member: discord.Member):
        if self.is_opt_disabled("join"):
            return None

        embed = LogEntry(colour=discord.Colour.green(), require_fields=False)
        embed.set_author(name=_("Member Joined"), icon_url=self.icon_uri(member))
        embed.set_footer(text=_("Member ID: {}").format(member.id))
        embed.description = _("Member {} joined\n\nAccount was created {}")\
            .format(member.mention, td_format(member.created_at - datetime.utcnow(), append_str=True))
        return embed

    def leave(self, member: discord.Member):
        if self.is_opt_disabled("leave"):
            return None

        embed = LogEntry(colour=discord.Colour.red(), require_fields=False)
        embed.set_author(name=_("Member Left"), icon_url=self.icon_uri(member))
        embed.set_footer(text=_("Member ID: {}").format(member.id))
        embed.description = _("Member {} left").format(member.mention)
        return embed

    def update(self, before: discord.Member, after: discord.Member):
        embed = LogEntry(colour=discord.Colour.blurple(), description=_("Member: {}").format(after.mention))
        embed.set_author(name=_("Member Updated"), icon_url=self.icon_uri(after))
        embed.set_footer(text=_("Member ID: {}").format(after.id))

        if hash(before.name) != hash(after.name) and self.is_opt_enabled("update", "name"):
            embed.add_diff_field(name=_("Username"), before=before.name, after=after.name)

        if hash(before.discriminator) != hash(after.discriminator) and self.is_opt_enabled("update", "discriminator"):
            embed.add_diff_field(name=_("Discriminator"), before=before.discriminator, after=after.discriminator)

        if before.nick != after.nick and self.is_opt_enabled("update", "nickname"):
            embed.add_diff_field(name=_("Nickname"), before=before.nick, after=after.nick)

        if before.roles != after.roles and self.is_opt_enabled("update", "roles"):
            embed.add_differ_field(name="Roles",
                                   before="\n".join([str(x) for x in before.roles if not x.is_default()]),
                                   after="\n".join([str(x) for x in after.roles if not x.is_default()]))

        return embed
