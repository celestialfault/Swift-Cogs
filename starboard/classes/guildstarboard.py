import asyncio

import discord

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.config import Group

from datetime import datetime, timedelta
from typing import Optional, Union, Dict, List

from .star import Star
from .starboardbase import StarboardBase


class GuildStarboard(StarboardBase):
    """Starboard for a specific Guild"""

    def __init__(self, guild: discord.Guild, config: Config, bot: Red):
        self.guild = guild
        self.config = config
        self.bot = bot
        self.queue = asyncio.Queue()
        self.migration_lock = asyncio.Lock()

        self._star_cache: Dict[int, Star] = {}
        self._blocked_users: List[int or discord.Member] = None
        self._min_stars: int = None
        self._ignored_channels: List[int or discord.TextChannel] = None
        self._channel: discord.TextChannel = False

    @property
    def guild_config(self) -> Group:
        """
        Get the guild's scoped Config
        :return: Guild scoped Group
        """
        return self.config.guild(self.guild)

    @property
    def messages(self) -> Group:
        """Returns Starboard's global message scope"""
        return self.config.custom("MESSAGES", self.guild.id)

    def __repr__(self):
        return "<GuildStarboard guild={0!r} cache_size={1}>".format(self.guild, len(self._star_cache))

    async def migrate(self) -> int:
        """Migrates guild-scoped message data to a generic message scope"""
        async with self.migration_lock:
            async with self.guild_config.messages() as old_data:
                migrated = len(old_data)
                # I also don't know why this is required.
                # Yes - a for loop was also attempted here.
                # It got through one item per migration call.
                # I don't know why.
                while len(old_data) > 0:
                    item = old_data.pop()
                    if not isinstance(item, dict) or 'message_id' not in item:
                        continue
                    await self.messages.set_raw(str(item.get("message_id")), value=item)
            return migrated

    def is_cached(self, message: discord.Message) -> bool:
        """Check if the message specified is in the star cache

        :param message: The message to check
        :return: True if the item is in the cache, False otherwise
        """
        return message.id in self._star_cache

    async def remove_from_cache(self, message: discord.Message) -> bool:
        """Remove the specified message from the guild's star cache

        :param message: The message to remove from the cache
        :return: True if the item was removed, False otherwise
        """
        if not self.is_cached(message):
            return False
        message_ = await self.message(message=message)
        if message_.in_queue:
            await message_.update_starboard_message()
        self._star_cache.pop(message.id)
        return True

    async def purge_cache(self, seconds_since_update: int = 30 * 60, dry_run: bool = False) -> int:
        """Purge the guild's starboard cache based on the entry's last updated timestamp

        Parameters
        ----------
        seconds_since_update: int
            The amount of seconds that must have passed since the last update for a Star for it to qualify
            to be removed from the cache. This can be set to 0 to clear *all* items.
            Defaults to 30 minutes
        dry_run: bool
            If this is set to True, qualifying items will only be counted instead of removed.
            Defaults to False

        Returns
        --------
        int
            The amount of items that were removed, or would have been removed if ``dry_run`` is True
        """
        check_ts = (datetime.utcnow() - timedelta(seconds=seconds_since_update)).timestamp()
        check_ts = datetime.fromtimestamp(check_ts)
        cache_copy = self._star_cache.copy()
        purged = 0
        for item in cache_copy:
            item = cache_copy[item]
            if item.last_update < check_ts:
                if not dry_run:
                    await self.remove_from_cache(item.message)
                purged += 1
        return purged

    async def handle_queue(self) -> None:
        """Handles this GuildStarboard's internal Star Queue."""
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

    async def message(self, *, message: discord.Message = None, message_id: int = None,
                      channel: discord.TextChannel = None, auto_create: bool = False) -> Optional[Star]:
        """Returns the Star object for the passed message

        Parameters
        ----------
        message: discord.Message
            The message to retrieve
        message_id: int
            A message to retrieve by ID
        channel: discord.TextChannel
            A text channel to use to attempt to resolve ``message_id``
        auto_create: bool
            Whether or not to automatically create the message's starboard entry

        Returns
        --------
        Optional[Star]
        """
        if not any([message, message_id]):
            raise ValueError

        if message_id:
            if channel is None:
                data = await self.messages.get_attr(str(message_id))(None)
                if data is None:
                    return None
                channel = self.bot.get_channel(data.get("channel_id", None))
                if channel is None:
                    return None
            try:
                message = await channel.get_message(message_id)
            except discord.HTTPException:
                return None

        if message is not None:
            if message.id not in self._star_cache:
                star = Star(self, message)
                await star.setup(auto_create=auto_create)
                self._star_cache[message.id] = star
            return self._star_cache[message.id]

    async def channel(self, channel: discord.TextChannel=False) -> Optional[discord.TextChannel]:
        """Set or clear the current guild's starboard

        Parameters
        -----------
        channel: discord.TextChannel
            The channel to set the guild's starboard channel to. If this is set to False,
            the current channel is returned instead.

        Returns
        --------
        Optional[discord.TextChannel]
            The current or newly set starboard channel

        Raises
        -------
        ValueError
            Raised if the passed channel is not in the current guild
        """
        if self._channel is False:
            self._channel = self.bot.get_channel(await self.guild_config.channel())
        if channel is not False:
            if channel and channel.guild.id != self.guild.id:
                raise ValueError("The passed TextChannel is not in the current Guild")
            self._channel = channel
            await self.guild_config.channel.set(getattr(channel, "id", None))
        return self._channel

    async def min_stars(self, amount: int=None) -> Optional[int]:
        """Set or get the amount of stars required for messages to appear in the guild's starboard channel

        Parameters
        -----------
        amount: int
            The amount of stars to require a message must receive to be sent to the starboard.
            If this is None, the current amount is returned instead.
            This must be at least one or more

        Returns
        --------
        int
            The amount of stars required. Only returned if amount is None
        None
            Returned when the minimum star amount is set successfully

        Raises
        ------
        ValueError
            Raised if ``amount`` is less than 1
        """
        if amount is not None:
            if amount < 1:
                raise ValueError("Amount must be at least one or greater")
            await self.guild_config.min_stars.set(amount)
            self._min_stars = amount
            return
        if self._min_stars is None:
            self._min_stars = await self.guild_config.min_stars()
        return self._min_stars

    async def is_ignored(self, obj: Union[discord.TextChannel, discord.Member]) -> bool:
        """Returns if the passed channel or member is ignored from having messages starred

        Parameters
        -----------
        obj: Union[discord.TextChannel, discord.Member]
            A member or text channel to check the ignore / block status for

        Returns
        --------
        bool
            A boolean value indicating if the channel or member is ignored or blocked from the guild's starboard
        """
        if isinstance(obj, discord.Member):
            if obj.bot:  # implicitly block bots from using the starboard
                return True

            # Integration with RequireRole
            require_role = self.bot.get_cog("RequireRole")
            if require_role and hasattr(require_role, "check") and await self.guild_config.respect_requirerole()\
                    and not await require_role.check(obj):
                return True

            if self._blocked_users is None:
                self._blocked_users = list(await self.guild_config.blocks())
            return obj.id in self._blocked_users

        if self._ignored_channels is None:
            self._ignored_channels = list(await self.guild_config.ignored_channels())
        return obj.id in self._ignored_channels or obj.id == getattr(await self.channel(), "id", None)

    async def ignore_channel(self, channel: discord.TextChannel):
        """Ignore a channel, preventing messages from being starred in it

        Parameters
        -----------
        channel: discord.TextChannel
            The text channel to ignore from the guild's starboard

        Returns
        --------
        bool
            A boolean value indicating if the channel was successfully ignored
        """
        if await self.is_ignored(channel):
            return False
        async with self.guild_config.ignored_channels() as ignores:
            ignores.append(channel.id)
            self._ignored_channels.append(channel.id)
        return True

    async def unignore_channel(self, channel: discord.TextChannel):
        """Unignore a channel, allowing messages to be starred in it again

        Parameters
        -----------
        channel: discord.TextChannel
            The text channel to unignore from the guild's starboard

        Returns
        --------
        bool
            A boolean value indicating if the channel was successfully unignored
        """
        if not await self.is_ignored(channel):
            return False
        async with self.guild_config.ignored_channels() as ignores:
            ignores.remove(channel.id)
            self._ignored_channels.remove(channel.id)
        return True

    async def block_member(self, member: discord.Member) -> bool:
        """Block a member from using the guild's starboard

        Parameters
        -----------
        member: discord.discord.Member
            The member to block from the guild's starboard

        Returns
        --------
        bool
            A boolean value indicating if the member was successfully blocked
        """
        if await self.is_ignored(member):
            return False
        async with self.guild_config.blocks() as blocks:
            blocks.append(member.id)
            self._blocked_users.append(member.id)
        return True

    async def unblock_member(self, member: discord.Member) -> bool:
        """Unblock a member and allow them to use the guild's starboard

        Parameters
        -----------
        member: discord.discord.Member
            The member to unblock from the guild's starboard

        Returns
        --------
        bool
            A boolean value indicating if the member was successfully unblocked
        """
        if not await self.is_ignored(member):
            return False
        async with self.guild_config.blocks() as blocks:
            blocks.remove(member.id)
            self._blocked_users.remove(member.id)
        return True
