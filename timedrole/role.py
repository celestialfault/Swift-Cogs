from datetime import datetime, timedelta

import discord

from timedrole.i18n import _

from cog_shared.odinair_libs.formatting import td_format


class TempRole:
    def __init__(self, role: discord.Role, guild, member: discord.Member, added_at: datetime, duration: int,
                 granted_by: int, **kwargs):
        from timedrole.guild import GuildRoles
        self.member = member
        self.role = role
        self.guild: GuildRoles = guild
        self.duration = timedelta(seconds=duration)
        self.added_at = added_at
        self.expiry_time = added_at + self.duration
        self.granted_by = guild.guild.get_member(granted_by) or granted_by
        self.hidden = kwargs.pop("hidden", False)
        self.reason = kwargs.pop("reason", None)

    def __str__(self):
        return str(self.role)

    @classmethod
    def from_data(cls, guild, member: discord.Member, data: dict):
        role = discord.utils.get(guild.roles, id=data.get("role_id", None))
        if role is None:
            return None
        return cls(role=role, member=member, guild=guild, **data)

    @property
    def has_expired(self) -> bool:
        return self.check_expired(member_has_role=True)

    def until_expires(self) -> str:
        expiry_ts = self.expiry_time - datetime.utcnow()
        return td_format(expiry_ts, append_str=True) if expiry_ts > timedelta() \
            else _("Queued for removal")

    def check_expired(self, *, member_has_role: bool) -> bool:
        return (self.role not in self.member.roles if member_has_role else False) \
               or self.expiry_time < datetime.utcnow()

    async def remove(self) -> None:
        await self.guild.remove(self.member, self.role)
        if self.role in self.member.roles:
            try:
                await self.member.remove_roles(self.role)
            except discord.HTTPException:
                pass
