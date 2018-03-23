from typing import Sequence

import discord

from redbot.core import Config
from redbot.core.bot import Red

from timedrole.role import TempRole


class GuildRoles:
    bot: Red = None
    config: Config = None

    def __init__(self, guild: discord.Guild):
        self.guild = guild

    @property
    def roles(self) -> Sequence[discord.Role]:
        return self.guild.roles

    async def all_temp_roles(self, *members: discord.Member) -> Sequence[TempRole]:
        members = [x.id for x in members]
        member_data = await self.config.all_members(self.guild)
        member_data = {uid: member_data[uid] for uid in member_data
                       if not len(members) or uid in members}
        roles = []
        for uid in member_data:
            member = self.guild.get_member(uid)
            if not member:
                continue
            temp_roles = member_data[uid]["roles"]
            for temp_role in temp_roles:
                try:
                    role = TempRole.from_data(self, member, temp_role)
                except ValueError:
                    await self.remove(member, temp_role.get("role_id"))
                else:
                    roles.append(role)
        return roles

    async def expired_roles(self, *members: discord.Member, **kwargs) -> Sequence[TempRole]:
        return [x for x in await self.all_temp_roles(*members) if x.check_expired(**kwargs)]

    async def active_roles(self, *members: discord.Member, **kwargs) -> Sequence[TempRole]:
        return [x for x in await self.all_temp_roles(*members) if not x.check_expired(**kwargs)]

    async def remove(self, member: discord.Member, role: discord.Role or int) -> None:
        role_id = role if isinstance(role, int) else role.id
        async with self.config.member(member).roles() as temp_roles:
            for item in temp_roles:
                if item.get("role_id", None) == role_id:
                    temp_roles.remove(item)
