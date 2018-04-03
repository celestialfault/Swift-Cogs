from typing import List, Type
from datetime import timedelta, datetime

import discord
from redbot.core.bot import Red

from timedrole.config import config


async def _get_roles(cls: Type["TempRole"], guild: discord.Guild, data: dict, *members: discord.Member):
    roles = []
    for mid in data:
        member = guild.get_member(mid)
        if member is None:
            continue
        if members and member not in members:
            continue
        for rid, role_data in data[mid].items():
            rid = int(rid)
            role = discord.utils.get(guild.roles, id=rid)
            if role is None:
                continue
            role = await cls.get(role=role, member=member)
            if role:
                if role.expired:
                    await role.remove_role()
                    continue
                roles.append(role)
    return roles


class TempRole:
    bot: Red = None

    def __init__(self, member: discord.Member, role: discord.Role, **kwargs):
        self.member = member
        self.role = role
        self.duration = timedelta(seconds=kwargs.pop("duration"))
        self.added_at = datetime.fromtimestamp(kwargs.pop("added_at"))
        self.added_by = self.member.guild.get_member(kwargs.get("added_by", None)) or kwargs.get("added_by", None)
        self.reason = kwargs.pop("reason", None)

    def __repr__(self):
        return f"<TempRole role={self.role!r} member={self.member!r} duration={self.duration}>"

    @property
    def expires_at(self):
        return self.added_at + self.duration

    @property
    def expired(self):
        return self.expires_at < datetime.utcnow()

    @property
    def guild(self) -> discord.Guild:
        return self.member.guild

    @property
    def dict(self):
        return {
            "duration": self.duration.total_seconds(),
            "added_at": self.added_at.timestamp(),
            "added_by": getattr(self.added_by, "id", self.added_by),
            "reason": self.reason
        }

    @classmethod
    async def all_roles(cls, guild: discord.Guild = None, *members: discord.Member) -> List["TempRole"]:
        all_roles: dict = await config.all_members(guild)
        roles = []
        if guild is None:
            for gid in all_roles:
                guild = cls.bot.get_guild(gid)
                if guild is None:
                    continue
                roles.extend(await _get_roles(cls, guild, all_roles[gid], *members))
        else:
            roles.extend(await _get_roles(cls, guild, all_roles, *members))
        return roles

    @classmethod
    async def get(cls, member: discord.Member, role: discord.Role):
        data = await config.member(member).get_raw(str(role.id), default=None)
        if data is None:
            return None
        return cls(member, role=role, **data)

    @classmethod
    async def create(cls, member: discord.Member, role: discord.Role, duration: timedelta,
                     added_by: discord.Member, *, reason: str = None):
        return await cls(member, role=role, duration=duration.total_seconds(), reason=reason,
                         added_by=added_by.id, added_at=datetime.utcnow().timestamp()).save()

    async def save(self):
        await config.member(self.member).set_raw(str(self.role.id), value=self.dict)
        return self

    async def remove_role(self, *, reason: str = None):
        await config.member(self.member).set_raw(str(self.role.id), value=None)
        if self.role in self.member.roles:
            try:
                await self.member.remove_roles(self.role, reason=reason)
            except discord.HTTPException:
                pass

    async def apply_role(self, *, reason: str = None):
        if self.role not in self.member.roles:
            try:
                await self.member.add_roles(self.role, reason=reason)
            except discord.HTTPException:
                pass
