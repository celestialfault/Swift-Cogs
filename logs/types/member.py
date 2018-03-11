from datetime import datetime
from difflib import Differ

import discord
from redbot.core.utils.chat_formatting import box

from ._base import BaseLog
from logs.logentry import LogEntry

from odinair_libs.formatting import td_format


class MemberLog(BaseLog):
    name = "members"
    descriptions = {
        "join": "Member joining",
        "leave": "Member leaving",
        "name": "Member username changes",
        "discriminator": "Member discriminator changes",
        "nickname": "Member nickname changes",
        "roles": "Member role changes"
    }

    def update(self, before: discord.Member, after: discord.Member, **kwargs):
        embed = LogEntry(colour=discord.Colour.blurple(), timestamp=datetime.utcnow(),
                         description=f"Member: {after.mention}")
        embed.set_author(name="Member Updated", icon_url=after.avatar_url_as(format="png"))
        embed.set_footer(text=f"User ID: {after.id}")

        if self.has_changed(before.name, after.name, "name"):
            embed.add_diff_field(name="Username", before=before.name, after=after.name)

        if self.has_changed(before.nick, after.nick, "nickname"):
            embed.add_diff_field(name="Nickname", before=before.nick, after=after.nick)

        if self.has_changed(before.discriminator, after.discriminator, "discriminator"):
            embed.add_diff_field(name="Discriminator", before=before.discriminator, after=after.discriminator)

        if self.has_changed(before.roles, after.roles, "roles"):
            before_roles = reversed(before.roles)
            after_roles = reversed(after.roles)
            changed = Differ().compare([str(x) for x in before_roles if not x.is_default()],
                                       [str(x) for x in after_roles if not x.is_default()])
            if changed:
                embed.add_field(name="Roles", value=box("\n".join(changed), lang="diff"))

        return embed

    def create(self, created: discord.Member, **kwargs):
        if self.settings.get("join", False) is False:
            return None

        account_age = td_format(created.joined_at - created.created_at, append_str=True)
        embed = LogEntry(colour=discord.Colour.green(),
                         description=f"Member {created.mention} joined\n\n"
                                     f"Account was created {account_age}",
                         require_fields=False, timestamp=created.joined_at)
        embed.set_author(name="Member Joined", icon_url=created.avatar_url_as(format="png"))
        embed.set_footer(text=f"User ID: {created.id}")
        return embed

    def delete(self, deleted: discord.Member, **kwargs):
        if self.settings.get("leave", False) is False:
            return None

        embed = LogEntry(colour=discord.Colour.red(),
                         description=f"Member {deleted.mention} left\n\n"
                                     f"They were a member for {td_format(datetime.utcnow() - deleted.joined_at)}",
                         require_fields=False, timestamp=datetime.utcnow())
        embed.set_author(name="Member Left", icon_url=deleted.avatar_url_as(format="png"))
        embed.set_footer(text=f"User ID: {deleted.id}")
        return embed
