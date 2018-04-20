from typing import Tuple

import discord

from redbot.core.bot import Red

from starboard.starboardguild import StarboardGuild
from starboard.base import StarboardBase, get_starboard

__all__ = ('StarboardUser',)


class StarboardUser(StarboardBase):
    def __init__(self, starboard: StarboardGuild, member: discord.Member):
        self.starboard = starboard
        self.member = member

    async def get_stats(self) -> Tuple[int, int]:
        """Retrieve the current user's statistics in the current guild"""

        messages = (await self.starboard.messages()).values()

        def validate_given(x):
            # members who have given a message a star used to be stored in a 'members' variable,
            # which may still exist instead of the current 'starrers'
            starrers = x.get('starrers', x.get('members', []))
            return self.member.id in starrers and not self.member.id == x.get('author_id', None)

        def validate_received(x):
            return x.get('author_id', None) == self.member.id

        given = len([x for x in messages if validate_given(x)])
        received = sum([len([y for y in x.get('starrers', x.get('members', [])) if y != self.member.id])
                        for x in messages if validate_received(x)])

        return given, received

    @staticmethod
    async def get_global_stats(bot: Red, user: discord.User) -> Tuple[int, int]:
        """Retrieve the total statistics for all guilds that the current user is in"""
        given = 0
        received = 0

        for guild in bot.guilds:
            if user not in guild.members:
                continue
            guild = await get_starboard(guild)
            guild_stats = await StarboardUser(guild, guild.get_member(user.id)).get_stats()
            given += guild_stats[0]
            received += guild_stats[1]

        return given, received
