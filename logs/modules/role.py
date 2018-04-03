import discord

from logs.core import Module, LogEntry, _

from cog_shared.odinair_libs.formatting import normalize


class RoleModule(Module):
    name = "role"
    friendly_name = _("Role")
    description = _("Role creation, deletion and update logging")
    settings = {
        "create": _("Role creations"),
        "delete": _("Role deletions"),
        "update": {
            "name": _("Role names"),
            "permissions": _("Role permissions"),
            "colour": _("Role colour"),
            "mentionable": _("If a role can be mentioned or not"),
            "hoist": _("If a role is displayed separately from online members"),
            "position": _("A roles position in the role hierarchy")
        }
    }

    def create(self, role: discord.Role):
        if self.is_opt_disabled("create"):
            return None

        embed = LogEntry(colour=discord.Colour.green(), require_fields=False)
        embed.set_author(name=_("Role Created"), icon_url=self.icon_uri())
        embed.set_footer(text=_("Role ID: {}").format(role.id))
        embed.description = _("Role: {}").format(role.mention)

        embed.add_field(name=_("Colour"),
                        value=str(role.colour) if role.colour != discord.Colour.default() else _("None"), inline=True)
        embed.add_field(name=_("Hoisted"), value=_("Yes") if role.hoist else _("No"), inline=True)
        embed.add_field(name=_("Mentionable"), value=_("Yes") if role.mentionable else _("No"), inline=True)

        embed.add_field(name=_("Permissions"),
                        value=", ".join([normalize(x, guild="server") for x, y in role.permissions if y]),
                        inline=False)

        return embed

    def delete(self, role: discord.Role):
        if self.is_opt_disabled("delete"):
            return None

        embed = LogEntry(colour=discord.Colour.red(), require_fields=False)
        embed.set_author(name=_("Role Deleted"), icon_url=self.icon_uri())
        embed.set_footer(text=_("Role ID: {}").format(role.id))
        embed.description = _("Role `{}` was deleted").format(role.name)
        return embed

    def update(self, before: discord.Role, after: discord.Role):
        embed = LogEntry(colour=discord.Colour.blurple())
        embed.set_author(name=_("Role Updated"), icon_url=self.icon_uri())
        embed.set_footer(text=_("Role ID: {}").format(after.id))
        embed.description = _("Role: {}").format(after.mention)

        if before.name != after.name and self.is_opt_enabled("update", "name"):
            embed.add_diff_field(name=_("Role Name"), before=before.name, after=after.name)

        if before.mentionable != after.mentionable and self.is_opt_enabled("update", "mentionable"):
            embed.add_diff_field(name=_("Mentionable"),
                                 before=_("Yes") if before.mentionable else _("No"),
                                 after=_("Yes") if after.mentionable else _("No"))

        if before.hoist != after.hoist and self.is_opt_enabled("update", "hoist"):
            embed.add_diff_field(name=_("Hoist"),
                                 before=_("Yes") if before.hoist else _("No"),
                                 after=_("Yes") if after.hoist else _("No"))

        if before.colour != after.colour and self.is_opt_enabled("update", "colour"):
            embed.add_diff_field(name=_("Colour"),
                                 before=str(before.colour) if before.colour != discord.Colour.default() else _("None"),
                                 after=str(after.colour) if after.colour != discord.Colour.default() else _("None"))

        if before.permissions.value != after.permissions.value and self.is_opt_enabled("update", "permissions"):
            embed.add_differ_field(name=_("Permissions"),
                                   before=[normalize(x, guild="server") for x, y in before.permissions if y],
                                   after=[normalize(x, guild="server") for x, y in after.permissions if y])

        if before.position != after.position and self.is_opt_enabled("update", "position"):
            embed.add_diff_field(name=_("Position"), before=before.position, after=after.position)

        return embed
