import discord

from logs.core import Module, LogEntry, i18n

from cog_shared.odinair_libs import normalize


class RoleModule(Module):
    name = "role"
    friendly_name = i18n("Role")
    description = i18n("Role creation, deletion and update logging")
    settings = {
        "create": i18n("Role creations"),
        "delete": i18n("Role deletions"),
        "update": {
            "name": i18n("Role names"),
            "permissions": i18n("Role permissions"),
            "colour": i18n("Role colour"),
            "mentionable": i18n("If a role can be mentioned or not"),
            "hoist": i18n("If a role is displayed separately from online members"),
            "position": i18n("A roles position in the role hierarchy")
        }
    }

    async def create(self, role: discord.Role):
        if not await self.is_opt_enabled("create"):
            return None

        embed = LogEntry(self, colour=discord.Colour.green(), require_fields=False,
                         description=i18n("Role: {}").format(role.mention))
        embed.set_author(name=i18n("Role Created"), icon_url=self.icon_uri())
        embed.set_footer(text=i18n("Role ID: {}").format(role.id))

        embed.add_field(name=i18n("Colour"),
                        value=str(role.colour) if role.colour != discord.Colour.default() else i18n("None"),
                        inline=True)
        embed.add_field(name=i18n("Hoisted"), value=i18n("Yes") if role.hoist else i18n("No"), inline=True)
        embed.add_field(name=i18n("Mentionable"), value=i18n("Yes") if role.mentionable else i18n("No"), inline=True)

        embed.add_field(name=i18n("Permissions"),
                        value=", ".join([normalize(x, guild="server") for x, y in role.permissions if y]),
                        inline=False)

        return embed

    async def delete(self, role: discord.Role):
        if not await self.is_opt_enabled("delete"):
            return None

        embed = LogEntry(self, colour=discord.Colour.red(), require_fields=False,
                         description=i18n("Role `{}` was deleted").format(role.name))
        embed.set_author(name=i18n("Role Deleted"), icon_url=self.icon_uri())
        embed.set_footer(text=i18n("Role ID: {}").format(role.id))
        return embed

    async def update(self, before: discord.Role, after: discord.Role):
        embed = LogEntry(self, colour=discord.Colour.blurple(), description=i18n("Role: {}").format(after.mention))
        embed.set_author(name=i18n("Role Updated"), icon_url=self.icon_uri())
        embed.set_footer(text=i18n("Role ID: {}").format(after.id))

        await embed.add_if_changed(name=i18n("Name"), before=before.name, after=after.name,
                                   config_opt=('update', 'name'))

        await embed.add_if_changed(name=i18n("Mentionable"), before=before.mentionable, after=after.mentionable,
                                   config_opt=('update', 'mentionable'))

        await embed.add_if_changed(name=i18n("Hoist"), before=before.hoist, after=after.hoist,
                                   config_opt=('update', 'hoist'))

        await embed.add_if_changed(name=i18n("Colour"), before=before.colour, after=after.colour,
                                   config_opt=('update', 'colour'),
                                   converter=lambda x: str(x) if x != discord.Colour.default() else i18n("None"))

        await embed.add_if_changed(name=i18n("Permissions"), diff=True, config_opt=('update', 'permissions'),
                                   before=[normalize(x, guild="server") for x, y in before.permissions if y],
                                   after=[normalize(x, guild="server") for x, y in after.permissions if y])

        await embed.add_if_changed(name=i18n("Position"), before=before.position, after=after.position,
                                   config_opt=('update', 'position'))

        return embed
