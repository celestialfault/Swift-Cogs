from datetime import datetime

import discord
from redbot.core.utils.chat_formatting import escape

from ._base import BaseLog
from odinair_libs.formatting import td_format, difference
from logs.logentry import LogEntry


def safe_escape(text: str, formatting: bool=True, mass_mentions: bool=True):
    """Calls escape(), but with proper handling of NoneType values"""
    if text is None:
        return ""
    return escape(text, formatting=formatting, mass_mentions=mass_mentions)


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

    async def update(self, before: discord.Member, after: discord.Member, **kwargs):
        ret = LogEntry(self, colour=discord.Colour.blurple())
        ret.set_title(icon_url=after.avatar_url, title="Member Updated", emoji="\N{MEMO}")
        ret.set_footer(footer="User ID: {0.id}".format(after), timestamp=datetime.utcnow())
        ret.description = "Member: **{0!s}**".format(after)

        if self.settings.get("name", False) is True and hash(before.name) != hash(after.name):
            ret.add_diff_field(title="Username", before=before.name, after=after.name)

        if self.settings.get("nickname", False) is True and hash(before.nick) != hash(after.nick):
            ret.add_diff_field(title="Nickname",
                               before=safe_escape(before.nick) if before.nick else "*No nickname*",
                               after=safe_escape(after.nick) if after.nick else "*No nickname*")

        if self.settings.get("discriminator", False) is True and before.discriminator != after.discriminator:
            ret.add_diff_field(title="Discriminator", before=before.discriminator, after=after.discriminator)

        if self.settings.get("roles", False) is True and before.roles != after.roles:
            added, removed = difference(before.roles, after.roles, check_val=False)
            if len(added) > 0:
                ret.add_field(title="Roles Added", value=", ".join([safe_escape(x.name) for x in added]))
            if len(removed) > 0:
                ret.add_field(title="Roles Removed", value=", ".join([safe_escape(x.name) for x in removed]))
        return ret

    def create(self, created: discord.Member, **kwargs):
        if not self.settings.get("join", False):
            return None

        ret = LogEntry(self, require_fields=False, colour=discord.Colour.green())
        ret.set_title(title="Member Joined", emoji="\N{WAVING HAND SIGN}", icon_url=created.avatar_url)
        ret.set_footer(footer="User ID: {0.id}".format(created), timestamp=created.joined_at)
        ret.description = "Member **{0!s}** joined".format(created)
        account_age = td_format(created.joined_at - created.created_at)
        ret.add_field(title="Account Age", value=account_age or "Brand new")
        return ret

    def delete(self, deleted: discord.Member, **kwargs):
        if not self.settings.get("leave", False):
            return None

        ret = LogEntry(self, require_fields=False, colour=discord.Colour.red())
        ret.set_title(title="Member Left", icon_url=deleted.avatar_url, emoji="\N{DOOR}")
        ret.set_footer(footer="User ID: {0.id}".format(deleted), timestamp=datetime.utcnow())
        ret.description = "Member **{0!s}** left".format(deleted)
        member_for = td_format(datetime.utcnow() - deleted.joined_at)
        ret.add_field(title="Member For", value=member_for)
        return ret
