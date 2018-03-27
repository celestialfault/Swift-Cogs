from typing import Dict

import discord

from starboard.starboardguild import StarboardGuild
from starboard.startype import StarType
from starboard.base import StarboardBase

__all__ = ('StarboardUser',)


class StarboardUser(StarboardBase):
    def __init__(self, starboard: StarboardGuild, member: discord.Member):
        self.starboard = starboard
        self.member = member
        self.guild = starboard.guild

    @property
    def guild_id(self):
        return str(self.guild.id)

    def _stats(self, *, member: discord.Member):
        # noinspection PyTypeChecker
        return self.config.user(member)

    async def get_stats(self, global_stats: bool = False) -> Dict[str, int]:
        stats = await self._stats(member=self.member).all()

        if global_stats:
            stats = {"given": sum([stats["given"][x] for x in stats.get("given", {})]),
                     "received": sum([stats["received"][x] for x in stats.get("received", {})])}
        else:
            stats["given"] = stats["given"].get(self.guild_id, 0)
            stats["received"] = stats["received"].get(self.guild_id, 0)

        return stats

    async def increment(self, star_type: StarType, amount: int = 1):
        if amount <= 0:
            raise ValueError("amount is equal to or less than zero")
        stats = dict(await self._stats(member=self.member).get_raw(str(star_type), default={}))
        if self.guild_id not in stats:
            stats[self.guild_id] = 0
        stats[self.guild_id] += amount
        await self._stats(member=self.member).set_raw(str(star_type), value=stats)

    async def decrement(self, star_type: StarType, amount: int = 1):
        if amount <= 0:
            raise ValueError("amount is equal to or less than zero")
        stats = dict(await self._stats(member=self.member).get_raw(str(star_type), default={}))
        if self.guild_id not in stats:
            stats[self.guild_id] = 0
        stats[self.guild_id] -= amount
        if stats[self.guild_id] <= 0:
            stats[self.guild_id] = 0
        await self._stats(member=self.member).set_raw(str(star_type), value=stats)
