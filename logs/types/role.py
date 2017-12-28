import discord
from redbot.core.utils.chat_formatting import escape

from logs.logentry import LogEntry
from logs.utils import difference, normalize
from .base import LogType


class RoleLogType(LogType):
    name = "roles"

    async def update(self, before: discord.Role, after: discord.Role, **kwargs):
        settings = await self.guild.config.roles.update()
        ret = LogEntry(self)
        ret.title = "Role updated"
        ret.description = escape("Role: **{0!s}**".format(after), mass_mentions=True)
        ret.emoji = "\N{MEMO}"
        ret.colour = discord.Colour.blurple()
        if before.name != after.name and settings["name"]:
            ret.add_field(title="Role Name", value="Role name changed to {0!s}".format(after))
        if before.position != after.position and settings["position"]:
            ret.add_field(title="Role Position", value="Role position changed from {0.position} to {1.position}"
                          .format(before, after))
        if before.colour != after.colour and settings["colour"]:
            ret.add_field(title="Role Colour", value="Role colour changed to {0.colour!s}".format(after))
        if before.hoist != after.hoist and settings["hoist"]:
            ret.add_field(title="Role Hoist", value="Role is {} hoisted".format("now" if after.hoist else "no longer"))
        if before.mentionable != after.mentionable and settings["mention"]:
            ret.add_field(title="Role Mention", value="Role is {} mentionable".format("now" if after.mentionable
                                                                                      else "no longer"))
        if before.permissions.value != after.permissions.value and settings["permissions"]:
            added, removed = difference(before.permissions, after.permissions, check_val=True)
            if len(added) > 0:
                ret.add_field(title="Permissions Granted",
                              value=", ".join([normalize(x, title_case=True, guild="server") for x in added]))
            if len(removed) > 0:
                ret.add_field(title="Permissions Revoked",
                              value=", ".join([normalize(x, title_case=True, guild="server") for x in removed]))
        return ret

    def create(self, created: discord.Role, **kwargs):
        ret = LogEntry(self)
        ret.title = "Role created"
        ret.emoji = "\N{LOWER LEFT BALLPOINT PEN}"
        ret.colour = discord.Colour.green()
        ret.require_fields = False
        ret.description = "Role **{0!s}** created".format(created)
        return ret

    def delete(self, deleted: discord.Role, **kwargs):
        ret = LogEntry(self)
        ret.title = "Role deleted"
        ret.emoji = "\N{WASTEBASKET}"
        ret.colour = discord.Colour.red()
        ret.require_fields = False
        ret.description = "Role **{0!s}** deleted".format(deleted)
        return ret
