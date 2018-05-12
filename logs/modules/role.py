import discord

from logs.core import Module, LogEntry, i18n

from cog_shared.swift_libs import normalize, formatting


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
            "position": i18n("A roles position in the role hierarchy"),
        },
    }

    async def create(self, role: discord.Role):
        if not await self.is_opt_enabled("create"):
            return None

        embed = LogEntry(
            self,
            colour=discord.Colour.green(),
            require_fields=False,
            description=i18n("Role: {}").format(role.mention),
        ).set_author(
            name=i18n("Role Created"), icon_url=self.icon_uri()
        ).set_footer(
            text=i18n("Role ID: {}").format(role.id)
        )

        embed.add_field(
            name=i18n("Colour"),
            value=str(role.colour) if role.colour != discord.Colour.default() else i18n("None"),
            inline=True,
        )
        embed.add_field(
            name=i18n("Hoisted"), value=i18n("Yes") if role.hoist else i18n("No"), inline=True
        )
        embed.add_field(
            name=i18n("Mentionable"),
            value=i18n("Yes") if role.mentionable else i18n("No"),
            inline=True,
        )

        embed.add_field(
            name=i18n("Permissions"),
            value=", ".join([normalize(x, guild="server") for x, y in role.permissions if y]),
            inline=False,
        )

        return embed

    async def delete(self, role: discord.Role):
        if not await self.is_opt_enabled("delete"):
            return None

        return LogEntry(
            self,
            colour=discord.Colour.red(),
            require_fields=False,
            description=i18n("Role `{}` was deleted").format(role.name),
        ).set_author(
            name=i18n("Role Deleted"), icon_url=self.icon_uri()
        ).set_footer(
            text=i18n("Role ID: {}").format(role.id)
        )

    async def update(self, before: discord.Role, after: discord.Role):
        embed = LogEntry(
            self,
            colour=discord.Colour.blurple(),
            description=i18n("Role: {}").format(after.mention),
        )
        embed.set_author(name=i18n("Role Updated"), icon_url=self.icon_uri())
        embed.set_footer(text=i18n("Role ID: {}").format(after.id))

        return await embed.add_multiple_changed(
            before,
            after,
            [
                {"name": i18n("Name"), "value": "name", "config_opt": ("update", "name")},
                {
                    "name": i18n("Mentionable"),
                    "value": "mentionable",
                    "config_opt": ("update", "mentionable"),
                },
                {"name": i18n("Hoist"), "value": "hoist", "config_opt": ("update", "hoist")},
                {
                    "name": i18n("Colour"),
                    "value": "colour",
                    "converter": lambda x: str(x)
                    if x != discord.Colour.default()
                    else i18n("None"),
                    "config_opt": ("update", "colour"),
                },
                {
                    "name": i18n("Permissions"),
                    "value": "permissions",
                    "diff": True,
                    "converter": lambda x: (
                        formatting.permissions.get(z, lambda: z)() for z, y in x if y
                    ),
                    "config_opt": ("update", "permissions"),
                },
                {
                    "name": i18n("Position"),
                    "value": "position",
                    "config_opt": ("update", "position"),
                },
            ],
        )
