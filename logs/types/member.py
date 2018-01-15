from datetime import datetime

import discord
from redbot.core.utils.chat_formatting import escape

from .base import LogType
from logs.utils import td_format, difference
from logs.logentry import LogEntry


def safe_escape(text: str, formatting: bool=True, mass_mentions: bool=True):
    """Calls escape(), but with proper handling of NoneType values"""
    if text is None:
        return ""
    return escape(text, formatting=formatting, mass_mentions=mass_mentions)


class MemberLogType(LogType):
    name = "members"

    async def update(self, before: discord.Member, after: discord.Member, **kwargs):
        settings = await self.guild.config.members()
        ret = LogEntry(self, colour=discord.Colour.blurple())
        ret.set_title(icon_url=after.avatar_url, title="Member updated", emoji="\N{MEMO}")
        ret.set_footer(footer="User ID: {0.id}".format(after), timestamp=datetime.utcnow())
        ret.description = "Member: **{0!s}**".format(after)

        if (before.name != after.name) and settings.get("name", False):
            ret.add_diff_field(title="Username Changed", before=str(before), after=str(after))

        if (before.nick != after.nick) and settings.get("nickname", False):
            ret.add_diff_field(title="Nickname Changed",
                               before=safe_escape(before.nick) if before.nick else "*No nickname*",
                               after=safe_escape(after.nick) if after.nick else "*No nickname*")

        if (before.roles != after.roles) and settings.get("roles", False):
            added, removed = difference(before.roles, after.roles, check_val=False)
            if len(added) > 0:
                ret.add_field(title="Roles Added", value=", ".join([safe_escape(x.name) for x in added]))
            if len(removed) > 0:
                ret.add_field(title="Roles Removed", value=", ".join([safe_escape(x.name) for x in removed]))
        return ret

    def create(self, created: discord.Member, **kwargs):
        ret = LogEntry(self, require_fields=False, colour=discord.Colour.green())
        ret.set_title(title="Member joined", emoji="\N{WAVING HAND SIGN}", icon_url=created.avatar_url)
        ret.set_footer(footer="User ID: {0.id}".format(created), timestamp=created.joined_at)
        ret.description = "Member **{0!s}** joined".format(created)
        account_age = td_format(created.joined_at - created.created_at)
        ret.add_field(title="Account Age", value=account_age or "Brand new")
        return ret

    def delete(self, deleted: discord.Member, **kwargs):
        ret = LogEntry(self, require_fields=False, colour=discord.Colour.red())
        ret.set_title(title="Member left", icon_url=deleted.avatar_url, emoji="\N{DOOR}")
        ret.set_footer(footer="User ID: {0.id}".format(deleted), timestamp=datetime.utcnow())
        ret.description = "Member **{0!s}** left".format(deleted)
        member_for = td_format(datetime.utcnow() - deleted.joined_at)
        ret.add_field(title="Member For", value=member_for)
        return ret
