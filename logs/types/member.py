from datetime import datetime

import discord
from redbot.core.utils.chat_formatting import escape

from .base import LogType
from logs.utils import td_format, difference
from logs.logentry import LogEntry


class MemberLogType(LogType):
    name = "members"

    async def update(self, before: discord.Member, after: discord.Member, **kwargs):
        settings = await self.guild.config.members.update()
        ret = LogEntry(self, self.guild)
        ret.icon_url = after.avatar_url
        ret.colour = discord.Colour.blurple()
        ret.emoji = "\N{MEMO}"
        ret.title = "Member updated"
        ret.description = "Member: {0!s}".format(after)
        if (before.name != after.name) and settings.get("name", False):
            ret.add_field(title="Username changed", value="Name changed from {0!s} to {1!s}".format(before, after))
        if (before.nick != after.nick) and settings.get("nickname", False):
            text = "Nickname changed from {0} to {1}".format(escape(before.nick, formatting=True, mass_mentions=True),
                                                             escape(after.nick, formatting=True, mass_mentions=True))
            ret.add_field(title="Nickname changed", value=text)
        if (before.roles != after.roles) and settings.get("roles", False):
            added, removed = difference(before.roles, after.roles, check_val=False)
            if len(added) > 0:
                role_names = ", ".join([x.name for x in added])
                ret.add_field(title="Roles added", value=role_names)
            if len(removed) > 0:
                role_names = ", ".join([x.name for x in removed])
                ret.add_field(title="Roles removed", value=role_names)
        return ret

    def create(self, created: discord.Member, **kwargs):
        account_age = td_format(created.created_at - created.joined_at)
        if not account_age:
            account_age = "brand new"
        else:
            account_age = account_age + " old"
        ret = LogEntry(self, self.guild)
        ret.icon_url = created.avatar_url
        ret.colour = discord.Colour.green()
        ret.emoji = "\N{WAVING HAND SIGN}"
        ret.title = "Member joined".format(created)
        ret.timestamp = created.joined_at
        ret.require_fields = False
        ret.description = "Member **{0!s}** joined\n\nAccount is {1}".format(created, account_age)
        return ret

    def delete(self, deleted: discord.Member, **kwargs):
        member_for = td_format(deleted.joined_at - datetime.utcnow())
        ret = LogEntry(self, self.guild)
        ret.icon_url = deleted.avatar_url
        ret.colour = discord.Colour.red()
        ret.emoji = "\N{DOOR}"
        ret.title = "Member left"
        ret.timestamp = datetime.utcnow()
        ret.require_fields = False
        ret.description = "Member **{0!s}** left\n\nThey were a member for {1}".format(deleted, member_for)
        return ret
