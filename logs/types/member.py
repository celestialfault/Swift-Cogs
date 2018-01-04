from datetime import datetime

import discord
from redbot.core.utils.chat_formatting import escape

from .base import LogType
from logs.utils import td_format, difference
from logs.logentry import LogEntry


class MemberLogType(LogType):
    name = "members"

    async def update(self, before: discord.Member, after: discord.Member, **kwargs):
        settings = await self.guild.config.members()
        ret = LogEntry(self, title="Member updated", emoji="\N{MEMO}", colour=discord.Colour.blurple(),
                       timestamp=datetime.utcnow())
        ret.icon_url = after.avatar_url
        ret.description = "Member: **{0!s}** ({0.id})".format(after)

        if (before.name != after.name) and settings.get("name", False):
            ret.add_diff_field(title="Username Changed", before=str(before), after=str(after))

        if (before.nick != after.nick) and settings.get("nickname", False):
            ret.add_diff_field(title="Nickname Changed",
                               before=escape(before.nick, formatting=True, mass_mentions=True),
                               after=escape(after.nick, formatting=True, mass_mentions=True))

        if (before.roles != after.roles) and settings.get("roles", False):
            added, removed = difference(before.roles, after.roles, check_val=False)
            if len(added) > 0:
                role_names = ", ".join([x.name for x in added])
                ret.add_field(title="Roles Added", value=role_names)
            if len(removed) > 0:
                role_names = ", ".join([x.name for x in removed])
                ret.add_field(title="Roles Removed", value=role_names)
        return ret

    def create(self, created: discord.Member, **kwargs):
        ret = LogEntry(self, title="Member joined", emoji="\N{WAVING HAND SIGN}", colour=discord.Colour.green(),
                       timestamp=created.joined_at)
        ret.icon_url = created.avatar_url
        ret.require_fields = False
        ret.description = "Member **{0!s}** ({0.id}) joined".format(created)
        account_age = td_format(created.joined_at - created.created_at)
        ret.add_field(title="Account Age", value=account_age or "Brand new")
        return ret

    def delete(self, deleted: discord.Member, **kwargs):
        ret = LogEntry(self)
        ret.icon_url = deleted.avatar_url
        ret.colour = discord.Colour.red()
        ret.emoji = "\N{DOOR}"
        ret.title = "Member left"
        ret.timestamp = datetime.utcnow()
        ret.require_fields = False
        ret.description = "Member **{0!s}** ({0.id}) left".format(deleted)
        member_for = td_format(datetime.utcnow() - deleted.joined_at)
        ret.add_field(title="Member For", value=member_for)
        return ret
