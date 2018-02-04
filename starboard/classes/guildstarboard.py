import asyncio
from asyncio import Queue

import discord

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.config import Group

from datetime import datetime, timedelta
from typing import Optional, Iterable, Union

from .star import Star
from .starboardbase import StarboardBase


class GuildStarboard(StarboardBase):
    """Starboard for a specific Guild"""

    def __init__(self, guild: discord.Guild, config: Config, bot: Red):
        self.guild = guild
        self._config = config
        self.bot = bot
        self.queue = Queue()
        self._star_cache = {}
        self._blocked_users = None
        self._min_stars = None
        self._ignored_channels = None

    @property
    def config(self) -> Group:
        """
        Get the guild's scoped Config
        :return: Guild scoped Group
        """
        return self._config.guild(self.guild)

    def __repr__(self):
        return "<GuildStarboard guild={0!r} cache_size={1}>".format(self.guild, len(self._star_cache))

    def is_cached(self, message: discord.Message) -> bool:
        """
        Check if the message specified is in the star cache
        :param message: The message to check
        :return: True if the item is in the cache, False otherwise
        """
        return message.id in self._star_cache

    async def remove_from_cache(self, message: discord.Message) -> bool:
        """
        Remove the specified message from the guild's star cache
        :param message: The message to remove from the cache
        :return: True if the item was removed, False otherwise
        """
        if not self.is_cached(message):
            return False
        _message = await self.message(message)
        if _message.in_queue:
            await _message.update_starboard_message()
        self._star_cache.pop(message.id)
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
                await self.remove_from_cache(item.message)
                purged += 1
        return purged

    async def housekeep(self) -> int:
        """
        Prune useless starboard data
        :return: The amount of items pruned
        """
        # Data storage framework when?
        # Seriously please, I'm desperate
        # Having to store this kind of stuff in a *guild-scoped Config group* shouldn't be necessary
        # And storing all this data shouldn't have to be done in a massive json dataset ;w;
        # (is it hard to tell that I miss being able to interact directly with mongodb like in Red v2?)
        pruned = 0
        async with self.config.messages() as messages:
            for message in messages:
                if len(message.get("members", [])) == 0:
                    if message.get("hidden", False):  # Preserve hidden entries regardless of if there's no stars
                        continue
                    messages.remove(message)
                    pruned += 1
        return pruned

    async def handle_queue(self) -> None:
        """
        Handles this GuildStarboard's internal Star Queue.
        :return: None
        """
        if self.queue.empty():
            return
        while not self.queue.empty():
            item = self.queue.get_nowait()
            if not isinstance(item, Star):
                continue
            if not item.in_queue:
                # Avoid re-updating messages if they've been updated before we got to them,
                # or if they were in the Queue more than once
                continue
            await item.update_starboard_message()
            asyncio.sleep(0.5)

    async def add_entry(self, message_id: int, channel_id: int, members: Iterable[int]=None,
                        starboard_message: int=None, hidden: bool=False) -> None:
        """
        Create a starboard entry
        :param message_id: The snowflake ID for the message in question
        :param channel_id: The snowflake ID for the channel the message is in
        :param members: A list of member IDs that have starred this message
        :param starboard_message: The starboard message snowflake ID
        :param hidden: A bool value of whether or not this message is hidden
        :return: None
        """
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

    async def message_by_id(self, message_id: int, channel_id: int=None, auto_create: bool=False) -> Optional[Star]:
        """
        Retrieve a Star object by it's message ID

        This requires the message to have been starred at least once if channel_id is not specified

        :param message_id: The snowflake ID of the message to retrieve
        :param channel_id: Optional channel snowflake ID to check, if omitted the message must have been starred before
        :param auto_create: Boolean value of whether or not to automatically create the message's starboard entry.
        This is only applicable when channel_id is specified.
        :return: Optional[Star]
        """
        if message_id in self._star_cache:
            return self._star_cache[message_id]
        if channel_id is not None:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                return None
            if channel.guild.id != self.guild.id:
                return None
            try:
                msg = await channel.get_message(message_id)
            except (discord.NotFound, discord.Forbidden):
                pass
            else:
                return await self.message(msg, auto_create=auto_create)
            return None
        # noinspection PyShadowingNames
        message = discord.utils.find(lambda msg: msg["message_id"] == message_id, await self.config.messages())
        if not message:
            return None
        channel = self.bot.get_channel(message["channel_id"])
        if not channel:
            return None
        try:
            message = await channel.get_message(message_id)
        except (discord.NotFound, discord.Forbidden):
            return None
        except discord.HTTPException:
            raise
        else:
            return await self.message(message)

    async def channel(self, channel: discord.TextChannel=False) -> Optional[discord.TextChannel]:
        """
        Set or clear the current guild's starboard

        :param channel: The channel to set the current starboard to.
        If this is False, the current channel is returned instead
        :return: Optional[discord.TextChannel]
        :raises ValueError: Raised if the passed channel is not in this GuildStarboard's specified Guild
        """
        if channel is not False:
            if channel and channel.guild.id != self.guild.id:
                raise ValueError("The passed TextChannel is not in the current Guild")
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

    async def is_ignored(self, channel_or_member: Union[discord.TextChannel, discord.Member]) -> bool:
        """
        Returns if the passed channel or member is ignored from having messages starred
        :param channel_or_member: A `discord.TextChannel` or `discord.Member` to check the ignore/block status for
        :return: True if the channel or member is ignored or blocked, False otherwise
        """
        if isinstance(channel_or_member, discord.Member):
            if channel_or_member.bot:  # implicitly block bots from using the starboard
                return True

            # Integration with RequireRole
            require_role = self.bot.get_cog("RequireRole")
            if require_role and hasattr(require_role, "check") and await self.config.respect_requirerole():
                if not await require_role.check(channel_or_member):
                    return True

            if self._blocked_users is None:
                self._blocked_users = list(await self.config.blocks())
            return channel_or_member.id in self._blocked_users

        if self._ignored_channels is None:
            self._ignored_channels = list(await self.config.ignored_channels())
        return channel_or_member.id in self._ignored_channels

    async def ignore_channel(self, channel: discord.TextChannel):
        """
        Ignore a channel, preventing messages from being starred in it
        :param channel: The `discord.TextChannel` to ignore
        :return: True if the channel was successfully ignored, False otherwise
        """
        if await self.is_ignored(channel):
            return False
        async with self.config.ignored_channels() as ignores:
            ignores.append(channel.id)
            self._ignored_channels.append(channel.id)
        return True

    async def unignore_channel(self, channel: discord.TextChannel):
        """
        Unignore a channel, allowing messages to be starred in it again
        :param channel: The `discord.TextChannel` to unignore
        :return: True if the channel was successfully unignored, False otherwise
        """
        if not await self.is_ignored(channel):
            return False
        async with self.config.ignored_channels() as ignores:
            ignores.remove(channel.id)
            self._ignored_channels.remove(channel.id)
        return True

    async def block_member(self, member: discord.Member) -> bool:
        """
        Block a member from using the guild's starboard
        :param member: The `discord.Member` to block
        :return: True if the member was successfully blocked, False otherwise
        """
        if await self.is_ignored(member):
            return False
        async with self.config.blocks() as blocks:
            blocks.append(member.id)
            self._blocked_users.append(member.id)
        return True

    async def unblock_member(self, member: discord.Member) -> bool:
        """
        Unblock a member and allow them to use the guild's starboard
        :param member: The `discord.Member` to unblock
        :return: True if the member was successfully unblocked, False otherwise
        """
        if not await self.is_ignored(member):
            return False
        async with self.config.blocks() as blocks:
            blocks.remove(member.id)
            self._blocked_users.remove(member.id)
        return True
