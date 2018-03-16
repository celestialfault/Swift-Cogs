from datetime import datetime

import discord

from logs.logentry import LogEntry
from ._base import BaseLogType, _

from odinair_libs.formatting import normalize


class RoleLogType(BaseLogType):
    name = "roles"
    descriptions = {
        "create": _("Role creations"),
        "delete": _("Role deletions"),
        "name": _("Role name"),
        "hoist": _("Role hoist status"),
        "mention": _("Role mentionable status"),
        "permissions": _("Role permissions"),
        "colour": _("Role colour"),
        "position": _("Role position changes")
    }

    def create(self, created: discord.Role, **kwargs):
        if not self.is_enabled("create"):
            return None

        embed = LogEntry(colour=discord.Colour.green(), description=_("Role {} was created").format(created.mention),
                         require_fields=False)
        embed.set_author(name=_("Role Created"), icon_url=self.icon_url())
        embed.set_footer(text=_("Role ID: {}").format(created.id))

        colour = created.colour if created.colour != discord.Colour.default() else None
        embed.add_field(name=_("Colour"), value=str(colour), inline=True)
        embed.add_field(name=_("Hoisted"), value=str(created.hoist), inline=True)
        embed.add_field(name=_("Mentionable"), value=str(created.mentionable), inline=True)
        embed.add_field(name=_("Permissions"), value=", ".join([normalize(x, guild="server")
                                                                for x, y in created.permissions if y]))
        return embed

    def update(self, before: discord.Role, after: discord.Role, **kwargs):
        embed = LogEntry(colour=discord.Colour.blurple(), description=_("Role: {}").format(after.mention),
                         timestamp=datetime.utcnow())

        embed.set_author(name=_("Role Updated"), icon_url=self.guild_icon_url)
        embed.set_footer(text=_("Role ID: {}").format(after.id))

        if self.has_changed(before.name, after.name, "name"):
            embed.add_diff_field(name=_("Name"), before=before.name, after=after.name)

        if self.has_changed(before.position, after.position, "position"):
            embed.add_diff_field(name=_("Position"), before=before.position, after=after.position)

        if self.has_changed(before.colour, after.colour, "colour"):
            before_colour = before.colour if before.colour != discord.Colour.default() else None
            after_colour = after.colour if after.colour != discord.Colour.default() else None
            embed.add_diff_field(name=_("Colour"), before=before_colour, after=after_colour)

        if self.has_changed(before.hoist, after.hoist, "hoist"):
            embed.add_diff_field(name=_("Hoisted"), before=before.hoist, after=after.hoist)

        if self.has_changed(before.mentionable, after.mentionable, "mention"):
            embed.add_diff_field(name=_("Mentionable"), before=before.mentionable, after=after.mentionable)

        if self.has_changed(before.permissions, after.permissions, "permissions"):
            embed.add_differ_field(name=_("Permissions"),
                                   before=[normalize(x[0], guild="server") for x in before.permissions if x[1]],
                                   after=[normalize(x[0], guild="server") for x in after.permissions if x[1]])

        return embed

    def delete(self, deleted: discord.Role, **kwargs):
        if not self.settings.get("delete", False):
            return None

        embed = LogEntry(colour=discord.Colour.red(), description=_("Role `{}` was deleted").format(str(deleted)),
                         require_fields=False, timestamp=datetime.utcnow())
        embed.set_author(name=_("Role Deleted"), icon_url=self.guild_icon_url)
        embed.set_footer(text=_("Role ID: {}").format(deleted.id))
        return embed
