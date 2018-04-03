from datetime import datetime

import discord

from redbot.core.utils.chat_formatting import inline

from logs.core import Module, LogEntry, _

from cog_shared.odinair_libs.formatting import td_format


class MemberModule(Module):
    name = "member"
    friendly_name = _("Member")
    description = _("Member joining, leaving, and update logging")
    settings = {
        "join": _("Member joining"),
        "leave": _("Member leaving"),
        "update": {
            "name": _("Member username changes"),
            "discriminator": _("Member discriminator changes"),
            "nickname": _("Member nickname changes"),
            "roles": _("Member role changes")
        }
    }

    def join(self, member: discord.Member):
        return (
            LogEntry(colour=discord.Color.green(), require_fields=False,
                     description=_("Member {} joined\n\nAccount was created {}").format(
                         member.mention, td_format(member.created_at - datetime.utcnow(), append_str=True)))
            .set_author(name=_("Member Joined"), icon_url=self.icon_uri(member))
            .set_footer(text=_("Member ID: {}").format(member.id))
        ) if self.is_opt_enabled("join") else None

    def leave(self, member: discord.Member):
        return (
            LogEntry(colour=discord.Color.red(), require_fields=False,
                     description=_("Member {} left").format(member.mention))
            .set_author(name=_("Member Left"), icon_url=self.icon_uri(member))
            .set_footer(text=_("Member ID: {}").format(member.id))
        ) if self.is_opt_enabled("leave") else None

    def update(self, before: discord.Member, after: discord.Member):
        embed = (
            LogEntry(colour=discord.Color.blurple(), description=_("Member: {}").format(after.mention))
            .set_author(name=_("Member Updated"), icon_url=self.icon_uri(after))
            .set_footer(text=_("Member ID: {}").format(after.id))
        )

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
