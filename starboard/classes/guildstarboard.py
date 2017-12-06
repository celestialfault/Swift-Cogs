from typing import Optional, Iterable

import discord
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.config import Group

from .star import Star
from .starboardbase import StarboardBase


class GuildStarboard(StarboardBase):
    """
    Starboard for a specified Guild.

    Don't create this directly - use the starboard function from any class that extends StarboardBase
    For example:
      bot.get_cog("Starboard").starboard(guild)
    """

    def __init__(self, guild: discord.Guild, config: Config, bot: Red):
        super().__init__()
        self.guild = guild
        self._config = config
        self.bot = bot
        self._star_cache = {}

    @property
    def config(self) -> Group:
        """
        Get the guild's config
        """
        return self._config.guild(self.guild)

    async def add_entry(self, message_id: int, channel_id: int, members: Iterable[int]=None, starboard_message: int=None,
                        hidden: bool=False) -> None:
        if members is None:
            members = []
        async with self.config.messages() as messages:
            messages.append({
                "message_id": message_id,
                "channel_id": channel_id,
                "members": members,
                "starboard_message": starboard_message,
                "hidden": hidden
            })

    async def message(self, message: discord.Message, *, auto_create: bool=False) -> Star:
        if message.id not in self._star_cache:
            star = Star(self, message)
            await star.setup(auto_create=auto_create)
            self._star_cache[message.id] = star
        return self._star_cache[message.id]

    async def message_by_id(self, message_id: int, data: dict=None):
        """
        Retrieve a Star object by it's message ID
        """
        async with self.config.messages() as messages:
            for message in messages:
                if message["message_id"] == message_id:
                    if data:
                        # Ensure we have the bare minimum we need to find this message again
                        data["message_id"] = message_id
                        messages[messages.index(message)] = data
                    return message

    async def channel(self, channel: discord.TextChannel=None, clear: bool=False) -> Optional[discord.TextChannel]:
        if channel or clear:
            await self.config.channel.set(channel.id if channel else None)
            return
        return self.bot.get_channel(await self.config.channel())

    async def min_stars(self, amount: int=None) -> Optional[int]:
        """
        Set or get the amount of stars required for messages to appear in the guild's starboard channel

        :param amount: Sets the amount of stars required and returns None
        :return: Optional[int] - Amount of stars required
        """
        if amount is not None:
            await self.config.min_stars.set(amount)
            return
        return await self.config.min_stars()
