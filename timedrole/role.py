from datetime import timedelta, datetime
from typing import Optional, Union

import discord

from redbot.core.bot import Red

from timedrole.config import config


class TempRole:
    bot = None  # type: Red

    def __init__(self, member: discord.Member, role: discord.Role, **kwargs):
        self.member = member
        self.role = role
        self.duration = timedelta(seconds=kwargs.pop("duration"))
        self.added_at = datetime.fromtimestamp(kwargs.pop("added_at"))
        self.added_by = self.guild.get_member(kwargs.get("added_by")) or kwargs.get("added_by")
        self.reason = kwargs.pop("reason", None)

    def __repr__(self):
        return "<TempRole role={self.role!r} member={self.member!r} duration={self.duration!r}>".format(self=self)

    @property
    def guild(self) -> discord.Guild:
        return self.member.guild

    @property
    def expires_at(self):
        return self.added_at + self.duration

    @property
    def expired(self):
        return self.expires_at <= datetime.utcnow()

    @property
    def as_dict(self):
        return {
            "duration": self.duration.total_seconds(),
            "added_at": self.added_at.timestamp(),
            "added_by": getattr(self.added_by, "id", self.added_by),
            "reason": self.reason
        }

    @classmethod
    async def all_roles(cls, *filters: Union[discord.Member, discord.Guild]):
        filters = set(filters)
        guilds = set([x.guild if isinstance(x, discord.Member) else x for x in filters])
        members = set([x for x in filters if isinstance(x, discord.Member)])

        all_roles = {}

        if guilds:
            for guild in guilds:
                all_roles[guild.id] = await config.all_members(guild)
        else:
            all_roles = await config.all_members()

        roles = []

        for gid in all_roles:
            guild = cls.bot.get_guild(gid)
            if guild is None:
                continue
            data = all_roles[gid]

            for mid in data:
                member = guild.get_member(mid)
                if member is None:
                    continue
                if members and member not in members:
                    continue

                for rid, role_data in data[mid].items():
                    # None is used as a replacement for previously added but since expired roles
                    if role_data is None:
                        continue

                    role = discord.utils.get(guild.roles, id=int(rid))
                    if role is None:
                        continue
                    role = cls(member, role=role, **role_data)

                    if role:
                        if role.expired:
                            await role.remove_role()
                            continue
                        roles.append(role)
        return roles

    @classmethod
    async def get(cls, member: discord.Member, role: discord.Role) -> Optional["TempRole"]:
        """Retrieve an existing timed role for a member"""
        data = await config.member(member).get_raw(str(role.id), default=None)
        if data is None:
            return None
        return cls(member, role=role, **data)

    @classmethod
    async def create(cls, member: discord.Member, role: discord.Role, duration: timedelta,
                     added_by: discord.Member, *, reason: str = None) -> "TempRole":
        """Create a timed role

        `apply_role` is not invoked for you, and must be manually done.

        Parameters
        -----------
        member: discord.Member
            The member to assign the role to
        role: discord.Role
            The role to assign to the given member
        duration: timedelta
            How long to give `role` to `member` for
        added_by: discord.Member
            The member who added the role to the user
        reason: Optional[str]
            An optional reason string. This is displayed in '[p]timedrole list'
        """
        self = cls(member, role=role, duration=duration.total_seconds(), reason=reason,
                   added_by=added_by.id, added_at=datetime.utcnow().timestamp())
        await self.save()
        return self

    async def save(self):
        """Save any changes made to the given role"""
        await config.member(self.member).set_raw(str(self.role.id), value=self.as_dict)

    async def remove_role(self, *, reason: str = None):
        """Remove this timed role from the assigned member"""
        await config.member(self.member).set_raw(str(self.role.id), value=None)
        if self.role in self.member.roles:
            try:
                await self.member.remove_roles(self.role, reason=reason)
            except discord.HTTPException:
                pass

    async def apply_role(self, *, reason: str = None):
        """Apply this timed role to the assigned member"""
        if self.role not in self.member.roles:
            try:
                await self.member.add_roles(self.role, reason=reason)
            except discord.HTTPException:
                pass
