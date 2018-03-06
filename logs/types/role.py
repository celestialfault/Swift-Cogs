from datetime import datetime

import discord

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

        ret = LogEntry(self, colour=discord.Colour.green(), require_fields=False,
                       description=f"{created.mention} was created")

        ret.set_title(title="Role Created")
        ret.set_footer(footer=f"Role ID: {created.id}", timestamp=created.created_at)

        colour = created.colour if created.colour != discord.Colour.default() else None
        ret.add_field(title="Colour", value=str(colour), inline=False)
        ret.add_field(title="Hoisted", value=str(created.hoist), inline=False)
        ret.add_field(title="Mentionable", value=str(created.mentionable), inline=False)
        ret.add_field(title="Permissions", value="\n".join([normalize(x, guild="server")
                                                            for x, y in created.permissions if y]))
        return ret

    def update(self, before: discord.Role, after: discord.Role, **kwargs):
        ret = LogEntry(self, colour=discord.Colour.blurple(), description=f"Role: {after.mention}")

        ret.set_title(title="Role Updated")
        ret.set_footer(footer=f"Role ID: {after.id}", timestamp=datetime.utcnow())

        if self.has_changed(before.name, after.name, "name"):
            ret.add_diff_field(title="Role Name", before=before.name, after=after.name)

        if self.has_changed(before.position, after.position, "position"):
            ret.add_diff_field(title="Role Position", before=before.position, after=after.position)

        if self.has_changed(before.colour, after.colour, "colour"):
            before_colour = before.colour if before.colour != discord.Colour.default() else None
            after_colour = after.colour if after.colour != discord.Colour.default() else None
            ret.add_diff_field(title="Role Colour", before=before_colour, after=after_colour)

        if self.has_changed(before.hoist, after.hoist, "hoist"):
            ret.add_diff_field(title="Hoisted", before=before.hoist, after=after.hoist)

        if self.has_changed(before.mentionable, after.mentionable, "mention"):
            ret.add_diff_field(title="Mentionable", before=before.mentionable, after=after.mentionable)

        if self.has_changed(before.permissions, after.permissions, "permissions"):
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

        ret = LogEntry(self, colour=discord.Colour.red(), require_fields=False,
                       description=f"`{deleted!s}` was deleted")
        ret.set_title(title="Role Deleted")
        ret.set_footer(footer=f"Role ID: {deleted.id}", timestamp=datetime.utcnow())
        return ret
