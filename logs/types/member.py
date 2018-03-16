from datetime import datetime

import discord

from ._base import BaseLogType
from logs.logentry import LogEntry
from logs.i18n import _

from odinair_libs.formatting import td_format


class MemberLogType(BaseLogType):
    name = "members"
    descriptions = {
        "join": _("Member joining"),
        "leave": _("Member leaving"),
        "name": _("Member username changes"),
        "discriminator": _("Member discriminator changes"),
        "nickname": _("Member nickname changes"),
        "roles": _("Member role changes")
    }

    def create(self, created: discord.Member, **kwargs):
        if self.is_disabled('join'):
            return None

        account_age = td_format(created.joined_at - created.created_at, append_str=True)
        embed = LogEntry(colour=discord.Colour.green(),
                         description=_("Member {} joined\n\n"
                                       "Account was created {}").format(created.mention, account_age),
                         require_fields=False, timestamp=created.joined_at)
        embed.set_author(name=_("Member Joined"), icon_url=self.icon_url(created))
        embed.set_footer(text=_("User ID: {}").format(created.id))
        return embed

    def update(self, before: discord.Member, after: discord.Member, **kwargs):
        embed = LogEntry(colour=discord.Colour.blurple(), timestamp=datetime.utcnow(),
                         description=_("Member: {}").format(after.mention))
        embed.set_author(name=_("Member Updated"), icon_url=self.icon_url(after))
        embed.set_footer(text=_("User ID: {}").format(after.id))

        if self.has_changed(before.name, after.name, "name"):
            embed.add_diff_field(name=_("Username"), before=before.name, after=after.name)

        if self.has_changed(before.nick, after.nick, "nickname"):
            embed.add_diff_field(name=_("Nickname"), before=before.nick, after=after.nick)

        if self.has_changed(before.discriminator, after.discriminator, "discriminator"):
            embed.add_diff_field(name=_("Discriminator"), before=before.discriminator, after=after.discriminator)

        if self.has_changed(before.roles, after.roles, "roles"):
            before_roles = [str(x) for x in reversed(before.roles) if not x.is_default()]
            after_roles = [str(x) for x in reversed(after.roles) if not x.is_default()]
            embed.add_differ_field(name=_("Roles"), before=before_roles, after=after_roles)

        return embed

    def delete(self, deleted: discord.Member, **kwargs):
        if self.is_disabled('leave'):
            return None

        embed = LogEntry(colour=discord.Colour.red(),
                         description=_("Member {} left\n\n"
                                       "They were a member for {}").format(deleted.mention,
                                                                           td_format(datetime.utcnow()
                                                                                     - deleted.joined_at)),
                         require_fields=False, timestamp=datetime.utcnow())
        embed.set_author(name=_("Member Left"), icon_url=self.icon_url(deleted))
        embed.set_footer(text=_("User ID: {}").format(deleted.id))
        return embed
