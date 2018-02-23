from datetime import datetime

import discord
from redbot.core.utils.chat_formatting import escape

from logs.logentry import LogEntry
from odinair_libs.formatting import difference, normalize
from ._base import BaseLog


class RoleLog(BaseLog):
    name = "roles"
    descriptions = {
        "create": "Role creations",
        "delete": "Role deletions",
        "name": "Role name",
        "hoist": "Role hoist status",
        "mention": "Role mentionable status",
        "permissions": "Role permissions",
        "colour": "Role colour",
        "position": "Role position changes (this option can be spammy!)"
    }

    def create(self, created: discord.Role, **kwargs):
        if not self.settings.get("create", False):
            return None

        ret = LogEntry(self, colour=discord.Colour.green(), require_fields=False)
        ret.set_title(title="Role Created", emoji="\N{LOWER LEFT BALLPOINT PEN}")
        colour = None if created.colour == discord.Colour.default() else created.colour
        ret.description = "\n".join([
            f"Role **{created!s}** created",
            f"Hoisted: **{created.hoist}**",
            f"Mentionable: **{created.mentionable}**",
            f"Colour: **{colour!s}**"
        ])
        ret.add_field(title="With Permissions",
                      value=", ".join([normalize(x, guild="server") for x, y in created.permissions if y]))
        ret.set_footer(footer=f"Role ID: {created.id}", timestamp=created.created_at)
        return ret

    async def update(self, before: discord.Role, after: discord.Role, **kwargs):
        ret = LogEntry(self, colour=discord.Colour.blurple())
        ret.description = escape(f"Role: **{after!s}**", mass_mentions=True)

        ret.set_title(title="Role Updated", emoji="\N{MEMO}")
        ret.set_footer(footer=f"Role ID: {after.id}", timestamp=datetime.utcnow())

        if before.name != after.name and self.settings.get("name", False):
            ret.add_diff_field(title="Role Name", before=before.name, after=after.name)

        if before.position != after.position and self.settings.get("position", False):
            ret.add_diff_field(title="Role Position", before=before.position, after=after.position)

        if before.colour != after.colour and self.settings.get("colour", False):
            before_colour = before.colour if before.colour != discord.Colour.default() else None
            after_colour = after.colour if after.colour != discord.Colour.default() else None
            ret.add_diff_field(title="Role Colour", before=before_colour, after=after_colour)

        if before.hoist != after.hoist and self.settings.get("hoist", False):
            ret.add_diff_field(title="Hoisted", before=before.hoist, after=after.hoist)

        if before.mentionable != after.mentionable and self.settings.get("mention", False):
            ret.add_diff_field(title="Mentionable", before=before.mentionable, after=after.mentionable)

        if before.permissions.value != after.permissions.value and self.settings.get("permissions", False):
            added, removed = difference(before.permissions, after.permissions, check_val=True)
            if added:
                ret.add_field(title="Permissions Granted",
                              value=", ".join([normalize(x, guild="server") for x in added]))
            if removed:
                ret.add_field(title="Permissions Revoked",
                              value=", ".join([normalize(x, guild="server") for x in removed]))

        return ret

    def delete(self, deleted: discord.Role, **kwargs):
        if not self.settings.get("delete", False):
            return None

        ret = LogEntry(self, colour=discord.Colour.red(), require_fields=False)
        ret.set_title(title="Role Deleted", emoji="\N{WASTEBASKET}")
        ret.description = f"Role **{deleted}** deleted"
        ret.set_footer(footer=f"Role ID: {deleted.id}", timestamp=datetime.utcnow())
        return ret
