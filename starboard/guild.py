import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import discord
from redbot.core.config import Group, Value

from cog_shared.swift_libs import IterableQueue
from starboard.base import StarboardBase
from starboard.log import log
from starboard.message import StarboardMessage

_janitors: Dict[int, asyncio.Task] = {}


class StarboardGuild(StarboardBase):

    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.update_queue = IterableQueue()
        self._cache: Dict[int, StarboardMessage] = {}

    def __repr__(self):
        return "<GuildStarboard guild={!r} cache_size={}>".format(self.guild, len(self._cache))

    @property
    def guild_config(self) -> Group:
        return self.config.guild(self.guild)

    @property
    def messages(self) -> Group:
        return self.config.custom("MESSAGES", self.guild.id)

    ###############################
    #   Settings

    @property
    def min_stars(self) -> Value:
        return self.guild_config.min_stars

    @property
    def selfstar(self) -> Value:
        return self.guild_config.selfstar

    @property
    def channel(self) -> Value:
        return self.guild_config.channel

    async def resolve_starboard(self) -> Optional[discord.TextChannel]:
        return self.bot.get_channel(await self.channel())

    @property
    def ignored(self) -> Group:
        return self.guild_config.ignored

    ###############################
    #   Janitor

    @property
    def janitor_task(self) -> Optional[asyncio.Task]:
        task = _janitors.get(self.guild.id, None)
        if task and task.done():
            try:
                # no pycharm, Task.exception() does not take
                # a 'or_None_if_no_exception_was_set' argument.
                # noinspection PyArgumentList
                exc = task.exception()
                if exc:
                    log.exception(
                        "Encountered exception in guild {} janitor task".format(self.guild.id),
                        exc_info=exc,
                    )
            except (asyncio.CancelledError, asyncio.InvalidStateError):
                pass
            del _janitors[self.guild.id]
        return _janitors.get(self.guild.id, None)

    async def setup_janitor(self, overwrite: bool = False):
        """Setup the current guild's starboard janitor task"""
        if self.janitor_task:
            if overwrite is False:
                return
            _janitors.pop(self.guild.id).cancel()
        if await self.resolve_starboard() is None:
            return
        log.debug("Setting up janitor task for guild {}".format(self.guild.id))
        _janitors[self.guild.id] = self.bot.loop.create_task(self._janitor())

    async def _janitor(self):
        """Internal janitor task method"""
        try:
            while True:
                await self.handle_queue()
                await self.purge_cache()
                await asyncio.sleep(6)
        except asyncio.CancelledError:
            log.debug(
                "Janitor for guild {} was cancelled; finishing message update queue & exiting"
                "".format(self.guild.id)
            )
            await self.handle_queue()

    ###############################
    #   Queue management

    async def handle_queue(self) -> None:
        """Handle all the items in the current starboard queue"""
        for item in self.update_queue:
            if not isinstance(item, StarboardMessage):
                continue
            if not item.in_queue:
                # Avoid re-updating messages if they've been updated before we got to them,
                # or if they were in the queue more than once
                continue
            await item.update_starboard_message()
            await asyncio.sleep(0.6)

    ###############################
    #   Caching

    def is_cached(self, message: discord.Message) -> bool:
        """Check if the given message is in the message cache"""
        return message.id in self._cache

    async def remove_from_cache(self, message: discord.Message, *, dump: bool = False) -> bool:
        """Remove the given message from the cache

        If the given message has an update queued, it'll be updated before being uncached.

        Parameters
        -----------
        message: discord.Message
            The message to remove from the cache
        dump: bool
            If this is True, the given message is dumped from the queue without updating it,
            instead of being updated and removed from the cache

        """
        star = await self.get_message(message=message, cache_only=True)
        if star is None:
            return False
        if star in self.update_queue:
            if dump:
                self.update_queue.remove(star)
            else:
                await star.update_starboard_message()
        self._cache.pop(message.id)
        return True

    async def purge_cache(
        self,
        seconds_since_update: int = 30 * 60,
        *,
        dry_run: bool = False,
        update_items: bool = True
    ) -> int:
        """Purge the message cache of stale items

        A stale item is defined as an item that hasn't had an update in X amount of seconds.
        By default, this is set to 30 minutes.

        Parameters
        -----------
        seconds_since_update: int
            How long until a message is considered stale and is eligible for being
            removed from the cache.
        dry_run: bool
            Whether or not this only counts the amount of messages being removed.
        update_items: bool
            If this is False, items will just be dumped from the cache without regard
            for if they have an update queued.

        Returns
        --------
        int
            The amount of messages removed from the cache
        """
        check_ts = (datetime.utcnow() - timedelta(seconds=seconds_since_update)).timestamp()
        check_ts = datetime.fromtimestamp(check_ts)
        purged = 0
        for item in self._cache.copy().values():
            if item.last_update < check_ts:
                if not dry_run:
                    await self.remove_from_cache(item.message, dump=not update_items)
                purged += 1
        return purged

    ###############################
    #   Messages

    @property
    def message_cache(self) -> List[StarboardMessage]:
        """Returns the current cached messages"""
        return list(self._cache.values())

    async def get_message(
        self,
        *,
        message: discord.Message = None,
        message_id: int = None,
        channel: discord.TextChannel = None,
        auto_create: bool = False,
        cache_only: bool = False
    ) -> Optional[StarboardMessage]:
        """Get a starboard message for the given message

        If `message_id` is given and `channel` is None, then the message
        must have been starred before to be able to resolve

        Either `message` or `message_id` must be given.

        Parameters
        -----------
        message: discord.Message
            A Discord message object
        message_id: int
            A Discord message ID to resolve. If this is given, `message` is always
            disregarded and treated as if it was set to None
        channel: Optional[discord.TextChannel]
            An optional channel to use to resolve `message_id`. This is required for `auto_create`
            to be able to function without passing a pre-existing Message object into `message`
        auto_create: bool
            Whether or not to auto-create the message entry. Either `message` or
            `message_id` and `channel` must be passed for this to function.
        cache_only: bool
            Whether or not to only retrieve messages from the internal cache

        Returns
        --------
        Optional[StarboardMessage]
        """
        if not any([message, message_id]):
            raise TypeError("neither 'message' nor 'message_id' arguments were given")

        if message_id and message_id in self._cache:
            return self._cache[message_id]
        elif message and message.id in self._cache:
            return self._cache[message.id]

        if cache_only is True:
            return None

        if message_id is not None:
            if channel is None:
                data = await self.messages.get_raw(str(message_id), default=None)
                if data is None:
                    return None
                channel = self.bot.resolve_starboard(data.get("channel_id", None))
                if channel is None:
                    return None

            try:
                message = await channel.get_message(message_id)
            except discord.HTTPException:
                return None

        if message is not None:
            if message.id not in self._cache:
                star = StarboardMessage(starboard=self, message=message)
                await star.load_data(auto_create=auto_create)
                self._cache[message.id] = star
            return self._cache[message.id]
        return None

    ###############################
    #   Ignores

    async def is_ignored(
        self, obj: Union[discord.TextChannel, discord.Member, discord.Message]
    ) -> bool:
        """Check if a member or channel is ignored from the starboard"""
        if isinstance(obj, discord.Message):
            return any([await self.is_ignored(obj.author), await self.is_ignored(obj.channel)])

        if isinstance(obj, discord.Member):
            return obj.id in await self.ignored.members()
        elif isinstance(obj, discord.TextChannel):
            return obj.id in await self.ignored.channels() or obj == await self.resolve_starboard()
        else:
            raise TypeError("obj is not of type TextChannel, Member or Message")

    async def ignore(self, obj: Union[discord.TextChannel, discord.Member]):
        """Ignore a member or channel"""
        if await self.is_ignored(obj):
            return False
        ignore_type = "members" if isinstance(obj, discord.Member) else "channels"
        async with self.guild_config.ignored.get_attr(ignore_type) as i:
            i.append(obj.id)
        return True

    async def unignore(self, obj: Union[discord.TextChannel, discord.Member]):
        """Unignore a member or channel"""
        if not await self.is_ignored(obj):
            return False
        ignore_type = "members" if isinstance(obj, discord.Member) else "channels"
        async with self.guild_config.ignored.get_attr(ignore_type) as i:
            i.remove(obj.id)
        return True
