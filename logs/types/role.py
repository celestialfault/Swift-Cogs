from datetime import datetime

import discord
from redbot.core.utils.chat_formatting import escape

from logs.logentry import LogEntry
from logs.utils import difference, normalize
from .base import LogType


class RoleLogType(LogType):
    name = "roles"

    async def update(self, before: discord.Role, after: discord.Role, **kwargs):
        settings = await self.guild.config.roles()
        ret = LogEntry(self)
        ret.title = "Role updated"
        ret.timestamp = datetime.utcnow()
        ret.description = escape("Role: **{0!s}**".format(after), mass_mentions=True)
        ret.emoji = "\N{MEMO}"
        ret.colour = discord.Colour.blurple()

        if before.name != after.name and settings.get("name", False):
            ret.add_diff_field(title="Name Changed", before=before.name, after=after.name)

        if before.position != after.position and settings.get("position", False):
            ret.add_diff_field(title="Position Changed", before=before.position, after=after.position)

        if before.colour != after.colour and settings.get("colour", False):
            ret.add_diff_field(title="Colour Changed", before=str(before.colour), after=str(after.colour))

        if before.hoist != after.hoist and settings.get("hoist", False):
            ret.add_field(title="Hoisted", value="Role is {} hoisted".format("now" if after.hoist else "no longer"))

        if before.mentionable != after.mentionable and settings.get("mention", False):
            ret.add_field(title="Mentionable", value="Role is {} mentionable".format("now" if after.mentionable
                                                                                     else "no longer"))

        if before.permissions.value != after.permissions.value and settings.get("permissions", False):
            added, removed = difference(before.permissions, after.permissions, check_val=True)
            if len(added) > 0:
                ret.add_field(title="Granted Permissions",
                              value=", ".join([normalize(x, title_case=True, guild="server") for x in added]))
            if len(removed) > 0:
                ret.add_field(title="Denied Permissions",
                              value=", ".join([normalize(x, title_case=True, guild="server") for x in removed]))

        return ret

    def create(self, created: discord.Role, **kwargs):
        ret = LogEntry(self)
        ret.title = "Role created"
        ret.emoji = "\N{LOWER LEFT BALLPOINT PEN}"
        ret.colour = discord.Colour.green()
        ret.require_fields = False
        ret.timestamp = created.created_at
        description = "Role **{0!s}** created\n" \
                      "Hoisted: **{0.hoist}**\n" \
                      "Mentionable: **{0.mentionable}**\n" \
                      "Colour: **{1}**"
        ret.description = description.format(created,
                                             created.colour if created.colour != discord.Colour.default() else None)
        ret.add_field(title="With Permissions", value=", ".join([normalize(x, title_case=True, guild="server")
                                                                 for x, y in created.permissions if y]))
        return ret

    def delete(self, deleted: discord.Role, **kwargs):
        ret = LogEntry(self)
        ret.title = "Role deleted"
        ret.emoji = "\N{WASTEBASKET}"
        ret.colour = discord.Colour.red()
        ret.require_fields = False
        ret.timestamp = datetime.utcnow()
        ret.description = "Role **{0!s}** deleted".format(deleted)
        return ret
