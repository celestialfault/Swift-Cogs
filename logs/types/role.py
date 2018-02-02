from datetime import datetime

import discord
from redbot.core.utils.chat_formatting import escape

from logs.logentry import LogEntry
from odinair_libs.formatting import difference, normalize
from .base import LogType


class RoleLogType(LogType):
    name = "roles"

    async def update(self, before: discord.Role, after: discord.Role, **kwargs):
        settings = await self.guild.config.roles()
        ret = LogEntry(self, colour=discord.Colour.blurple())
        ret.set_title(title="Role Updated", emoji="\N{MEMO}")
        ret.set_footer(footer="Role ID: {0.id}".format(after), timestamp=datetime.utcnow())
        ret.description = escape("Role: **{0!s}**".format(after), mass_mentions=True)

        if before.name != after.name and settings.get("name", False):
            ret.add_diff_field(title="Role Name", before=before.name, after=after.name)

        if before.position != after.position and settings.get("position", False):
            ret.add_diff_field(title="Role Position", before=before.position, after=after.position)

        if before.colour != after.colour and settings.get("colour", False):
            before_colour = before.colour if before.colour != discord.Colour.default() else None
            after_colour = after.colour if after.colour != discord.Colour.default() else None
            ret.add_diff_field(title="Role Colour", before=before_colour, after=after_colour)

        if before.hoist != after.hoist and settings.get("hoist", False):
            ret.add_field(title="Hoisted",
                          value="Role is {} hoisted".format("now" if after.hoist else "no longer"))

        if before.mentionable != after.mentionable and settings.get("mention", False):
            ret.add_field(title="Mentionable", value="Role is {} mentionable".format("now" if after.mentionable
                                                                                            else "no longer"))

        if before.permissions.value != after.permissions.value and settings.get("permissions", False):
            added, removed = difference(before.permissions, after.permissions, check_val=True)
            if len(added) > 0:
                ret.add_field(title="Permissions Granted",
                              value=", ".join([normalize(x, title_case=True, guild="server") for x in added]))
            if len(removed) > 0:
                ret.add_field(title="Permissions Revoked",
                              value=", ".join([normalize(x, title_case=True, guild="server") for x in removed]))

        return ret

    def create(self, created: discord.Role, **kwargs):
        ret = LogEntry(self, colour=discord.Colour.green(), require_fields=False)
        ret.set_title(title="Role created", emoji="\N{LOWER LEFT BALLPOINT PEN}")
        ret.description = "Role **{0!s}** created\n" \
                          "Hoisted: **{0.hoist}**\n" \
                          "Mentionable: **{0.mentionable}**\n" \
                          "Colour: **{1}**".format(created,
                                                   created.colour if created.colour != discord.Colour.default()
                                                   else None)
        ret.add_field(title="With Permissions", value=", ".join([normalize(x, title_case=True, guild="server")
                                                                 for x, y in created.permissions if y]))
        ret.set_footer(footer="Role ID: {0.id}".format(created), timestamp=created.created_at)
        return ret

    def delete(self, deleted: discord.Role, **kwargs):
        ret = LogEntry(self, colour=discord.Colour.red(), require_fields=False)
        ret.set_title(title="Role deleted", emoji="\N{WASTEBASKET}")
        ret.description = "Role **{0!s}** deleted".format(deleted)
        ret.set_footer(footer="Role ID: {0.id}".format(deleted), timestamp=datetime.utcnow())
        return ret
