import discord

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.config import Group

from datetime import datetime, timedelta
from typing import Optional, Iterable

from .star import Star
from .starboardbase import StarboardBase


class GuildStarboard(StarboardBase):
    """Starboard for a specific Guild"""

    _star_cache = {}
    _blocked_users = None
    _min_stars = None

    def __init__(self, guild: discord.Guild, config: Config, bot: Red):
        self.guild = guild
        self._config = config
        self.bot = bot

    @property
    def config(self) -> Group:
        return self._config.guild(self.guild)

    def __repr__(self):
        return "<GuildStarboard guild={0!r}>".format(self.guild)

    def is_cached(self, message: discord.Message) -> bool:
        """Check if the message specified is in the star cache"""
        return message.id in self._star_cache

    def remove_from_cache(self, message: discord.Message) -> bool:
        """Remove the specified message from the guild's star cache"""
        if not self.is_cached(message):
            return False
        del self._star_cache[message.id]
        return True

    async def purge_cache(self, seconds_since_update: int=30 * 60) -> int:
        """
        Purge the guild's starboard cache based on the entry's last updated timestamp
        :param seconds_since_update: The amount of seconds that must have passed since the last update.
        Set this to 0 to clear all cache entries
        :return: The amount of entries cleared from the cache
        """
        check_ts = (datetime.utcnow() - timedelta(seconds=seconds_since_update)).timestamp()
        check_ts = datetime.fromtimestamp(check_ts)
        cache_copy = self._star_cache.copy()
        purged = 0
        for item in cache_copy:
            item = cache_copy[item]
            if item.last_update < check_ts:
                self.remove_from_cache(item.message)
                purged += 1
        return purged

    async def add_entry(self, message_id: int, channel_id: int, members: Iterable[int]=None,
                        starboard_message: int=None, hidden: bool=False) -> None:
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

    async def message(self, message: discord.Message, auto_create: bool=False) -> Star:
        """
        Returns the Star object for the passed message

        :param message: The message to get a Star object for
        :param auto_create: Whether or not to automatically create the starboard entry if it doesn't exist
        :return: The message's Star object
        """
        if message.id not in self._star_cache:
            star = Star(self, message)
            await star.setup(auto_create=auto_create)
            self._star_cache[message.id] = star
        return self._star_cache[message.id]

    async def message_by_id(self, message_id: int) -> Optional[Star]:
        """
        Retrieve a Star object by it's message ID

        This requires the message to have been starred at least once

        :param message_id: The snowflake ID of the message to retrieve
        :return: Optional[Star]
        """
        if message_id in self._star_cache:
            return self._star_cache[message_id]
        messages = await self.config.messages()
        message = discord.utils.find(lambda msg: msg["message_id"] == message_id, messages)
        if not message:
            return None
        channel = self.bot.get_channel(message["channel_id"])
        if not channel:
            return None
        try:
            message = await channel.get_message(message_id)
        except discord.NotFound:
            return None
        except discord.Forbidden:
            return None
        except discord.HTTPException:
            raise
        else:
            return await self.message(message)

    async def channel(self, channel: discord.TextChannel=None, clear: bool=False) -> Optional[discord.TextChannel]:
        """
        Set or clear the current guild's starboard

        :param channel: The channel to set the current starboard to - to clear, pass None and set clear to True
        :param clear: Whether or not to clear the current channel - pass None as the channel with this value
        :return: Optional[discord.TextChannel]
        :raises ValueError: Raised if the passed channel is not in the current Guild
        """
        if channel or clear:
            if channel and channel.guild.id != self.guild.id:
                raise ValueError("Passed TextChannel object is not in the current Guild")
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
            if amount <= 0:
                raise ValueError("Amount must be a non-zero number")
            await self.config.min_stars.set(amount)
            self._min_stars = amount
            return
        if self._min_stars is None:
            self._min_stars = await self.config.min_stars()
        return self._min_stars

    async def is_blocked(self, member: discord.Member) -> bool:
        """
        Returns if the passed member is blocked from using the starboard
        """
        if member.bot:  # implicitly block bots from using the starboard
            return True
        if self._blocked_users is None:
            async with self.config.blocks() as blocks:
                self._blocked_users = list(blocks)
        return member.id in self._blocked_users

    async def block(self, member: discord.Member) -> bool:
        """
        Blocks the passed member from using the guild's starboard
        """
        if await self.is_blocked(member):
            return False
        async with self.config.blocks() as blocks:
            self._blocked_users.append(member.id)
            blocks.append(member.id)
        return True

    async def unblock(self, member: discord.Member) -> bool:
        """
        Unblocks the passed member from using the guild's starboard
        """
        if not await self.is_blocked(member):
            return False
        async with self.config.blocks() as blocks:
            del self._blocked_users[self._blocked_users.index(member.id)]
            blocks.remove_star(member.id)
        return True
