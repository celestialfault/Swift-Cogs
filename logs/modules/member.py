from datetime import datetime

import discord

from redbot.core.utils.chat_formatting import inline

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

        if self.has_changed(before.name, after.name, conf_setting=('update', 'name')):
            embed.add_diff_field(name=_("Username"), before=before.name, after=after.name)

        if self.has_changed(before.discriminator, after.discriminator, conf_setting=('update', 'discriminator')):
            embed.add_diff_field(name=_("Discriminator"), before=before.discriminator, after=after.discriminator)

        if self.has_changed(before.nick, after.nick, conf_setting=('update', 'nickname')):
            embed.add_diff_field(name=_("Nickname"),
                                 before=before.nick or inline(_("None")),
                                 after=after.nick or inline(_("None")))

        if self.has_changed(before.roles, after.roles, conf_setting=('update', 'roles')):
            embed.add_differ_field(name="Roles",
                                   before=[str(x) for x in before.roles if not x.is_default()],
                                   after=[str(x) for x in after.roles if not x.is_default()])

        return embed
