from datetime import datetime

import discord

from logs.logentry import LogEntry
from ._base import BaseLog

from odinair_libs.formatting import normalize


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
        if not self.is_enabled("create"):
            return None

        embed = LogEntry(colour=discord.Colour.green(), description=f"{created.mention} was created",
                         require_fields=False)
        embed.set_author(name="Role Created", icon_url=self.guild_icon_url)
        embed.set_footer(text=f"Role ID: {created.id}")

        colour = created.colour if created.colour != discord.Colour.default() else None
        embed.add_field(name="Colour", value=str(colour), inline=False)
        embed.add_field(name="Hoisted", value=str(created.hoist), inline=False)
        embed.add_field(name="Mentionable", value=str(created.mentionable), inline=False)
        embed.add_field(name="Permissions", value="\n".join([normalize(x, guild="server")
                                                            for x, y in created.permissions if y]))
        return embed

    def update(self, before: discord.Role, after: discord.Role, **kwargs):
        embed = LogEntry(colour=discord.Colour.blurple(), description=f"Role: {after.mention}",
                         timestamp=datetime.utcnow())

        embed.set_author(name="Role Updated", icon_url=self.guild_icon_url)
        embed.set_footer(text=f"Role ID: {after.id}")

        if self.has_changed(before.name, after.name, "name"):
            embed.add_diff_field(name="Role Name", before=before.name, after=after.name)

        if self.has_changed(before.position, after.position, "position"):
            embed.add_diff_field(name="Role Position", before=before.position, after=after.position)

        if self.has_changed(before.colour, after.colour, "colour"):
            before_colour = before.colour if before.colour != discord.Colour.default() else None
            after_colour = after.colour if after.colour != discord.Colour.default() else None
            embed.add_diff_field(name="Role Colour", before=before_colour, after=after_colour)

        if self.has_changed(before.hoist, after.hoist, "hoist"):
            embed.add_diff_field(name="Hoisted", before=before.hoist, after=after.hoist)

        if self.has_changed(before.mentionable, after.mentionable, "mention"):
            embed.add_diff_field(name="Mentionable", before=before.mentionable, after=after.mentionable)

        if self.has_changed(before.permissions, after.permissions, "permissions"):
            embed.add_differ_field(name="Permissions",
                                   before=[normalize(x[0], guild="server") for x in before.permissions if x[1]],
                                   after=[normalize(x[0], guild="server") for x in after.permissions if x[1]])

        return embed

    def delete(self, deleted: discord.Role, **kwargs):
        if not self.settings.get("delete", False):
            return None

        embed = LogEntry(colour=discord.Colour.red(), description=f"`{deleted!s}` was deleted", require_fields=False,
                         timestamp=datetime.utcnow())
        embed.set_author(name="Role Deleted", icon_url=self.guild_icon_url)
        embed.set_footer(text=f"Role ID: {deleted.id}")
        return embed
