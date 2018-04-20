import discord

from logs.core import Module, LogEntry, _

from cog_shared.odinair_libs import normalize


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

    async def create(self, role: discord.Role):
        if not await self.is_opt_enabled("create"):
            return None

        embed = LogEntry(self, colour=discord.Colour.green(), require_fields=False,
                         description=_("Role: {}").format(role.mention))
        embed.set_author(name=_("Role Created"), icon_url=self.icon_uri())
        embed.set_footer(text=_("Role ID: {}").format(role.id))

        embed.add_field(name=_("Colour"),
                        value=str(role.colour) if role.colour != discord.Colour.default() else _("None"), inline=True)
        embed.add_field(name=_("Hoisted"), value=_("Yes") if role.hoist else _("No"), inline=True)
        embed.add_field(name=_("Mentionable"), value=_("Yes") if role.mentionable else _("No"), inline=True)

        embed.add_field(name=_("Permissions"),
                        value=", ".join([normalize(x, guild="server") for x, y in role.permissions if y]),
                        inline=False)

        return embed

    async def delete(self, role: discord.Role):
        if not await self.is_opt_enabled("delete"):
            return None

        embed = LogEntry(self, colour=discord.Colour.red(), require_fields=False,
                         description=_("Role `{}` was deleted").format(role.name))
        embed.set_author(name=_("Role Deleted"), icon_url=self.icon_uri())
        embed.set_footer(text=_("Role ID: {}").format(role.id))
        return embed

    async def update(self, before: discord.Role, after: discord.Role):
        embed = LogEntry(self, colour=discord.Colour.blurple(), description=_("Role: {}").format(after.mention))
        embed.set_author(name=_("Role Updated"), icon_url=self.icon_uri())
        embed.set_footer(text=_("Role ID: {}").format(after.id))

        await embed.add_if_changed(name=_("Name"), before=before.name, after=after.name, config_opt=('update', 'name'))

        await embed.add_if_changed(name=_("Mentionable"), before=before.mentionable, after=after.mentionable,
                                   config_opt=('update', 'mentionable'))

        await embed.add_if_changed(name=_("Hoist"), before=before.hoist, after=after.hoist,
                                   config_opt=('update', 'hoist'))

        await embed.add_if_changed(name=_("Colour"), before=before.colour, after=after.colour,
                                   config_opt=('update', 'colour'),
                                   converter=lambda x: str(x) if x != discord.Colour.default() else _("None"))

        await embed.add_if_changed(name=_("Permissions"), diff=True, config_opt=('update', 'permissions'),
                                   before=[normalize(x, guild="server") for x, y in before.permissions if y],
                                   after=[normalize(x, guild="server") for x, y in after.permissions if y])

        await embed.add_if_changed(name=_("Position"), before=before.position, after=after.position,
                                   config_opt=('update', 'position'))

        return embed
