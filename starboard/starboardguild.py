from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any

import asyncio

import discord

from redbot.core.config import Group

from starboard.starboardmessage import StarboardMessage
from starboard.base import StarboardBase
from starboard.log import log

from cog_shared.odinair_libs import IterQueue

_janitors = {}  # type: Dict[int, asyncio.Task]
__all__ = ('StarboardGuild',)


class StarboardGuild(StarboardBase):
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.update_queue = IterQueue()

        self._migration_lock = asyncio.Lock()
        self._cache = {}  # type: Dict[int, StarboardMessage]
        self._settings = None  # type: Dict[str, Any]
        self._settings_changed = False

    def __repr__(self):
        return "<GuildStarboard guild={0!r} cache_size={1}>".format(self.guild, len(self._cache))

    async def init(self):
        log.debug("Initializing guild {}".format(self.guild.id))
        await self._reload_settings()

    @property
    def guild_config(self) -> Group:
        return self.config.guild(self.guild)

    @property
    def messages(self) -> Group:
        return self.config.custom("MESSAGES", self.guild.id)

    ###############################
    #   Settings

    @property
    def min_stars(self):
        return self._settings["min_stars"]

    @min_stars.setter
    def min_stars(self, min_stars: int):
        if min_stars is self.min_stars:
            return
        self._settings["min_stars"] = min_stars
        self._settings_changed = True

    @property
    def selfstar(self):
        return self._settings["selfstar"]

    @selfstar.setter
    def selfstar(self, selfstar: bool):
        self._settings["selfstar"] = selfstar
        self._settings_changed = True

    @property
    def channel(self):
        return self.bot.get_channel(self._settings["channel"])

    @channel.setter
    def channel(self, channel: Optional[discord.TextChannel]):
        if channel and channel.guild.id != self.guild.id:
            raise ValueError("The passed TextChannel is not in the current Guild")
        self._settings["channel"] = getattr(channel, "id", None)
        self._settings_changed = True
        self.setup_janitor(overwrite=False)

    @property
    def ignored(self):
        return self._settings["ignored"].copy()

    async def _reload_settings(self):
        self._settings = await self.config.guild(self.guild).all()

    async def _save_settings(self):
        if self._settings_changed:
            await self.guild_config.set(self._settings)
            self._settings_changed = False

    ###############################
    #   Janitor

    @property
    def janitor_task(self):
        task = _janitors.get(self.guild.id, None)
        if task and task.done():
            try:
                # noinspection PyArgumentList
                exc = task.exception()
                if exc:
                    log.exception("Encountered exception in guild {} janitor task".format(self.guild.id), exc_info=exc)
            except (asyncio.CancelledError, asyncio.InvalidStateError):
                pass
            del _janitors[self.guild.id]
        return _janitors.get(self.guild.id, None)

    def setup_janitor(self, overwrite: bool = False):
        if self.janitor_task:
            if overwrite is False:
                return
            _janitors.pop(self.guild.id).cancel()
        log.debug("Setting up janitor task for guild {}".format(self.guild.id))
        _janitors[self.guild.id] = self.bot.loop.create_task(self._janitor())

    async def _janitor(self):
        try:
            while True:
                await self.handle_queue()
                await self.purge_cache()
                await self._save_settings()
                await asyncio.sleep(8)
        except asyncio.CancelledError:
            log.debug("Janitor for guild {} was cancelled; finishing message update queue & exiting"
                      "".format(self.guild.id))
            await self.handle_queue()
            await self._save_settings()

    ###############################
    #   Queue management

    async def handle_queue(self) -> None:
        for item in self.update_queue:
            if not isinstance(item, StarboardMessage):
                continue
            if not item.in_queue:
                # Avoid re-updating messages if they've been updated before we got to them,
                # or if they were in the Queue more than once
                continue
            await item.update_starboard_message()
            await asyncio.sleep(0.5)

    ###############################
    #   Caching

    def is_cached(self, message: discord.Message) -> bool:
        return message.id in self._cache

    async def remove_from_cache(self, message: discord.Message) -> bool:
        star = await self.get_message(message=message, cache_only=True)
        if star is None:
            return False
        if star.in_queue:
            await star.update_starboard_message()
        self._cache.pop(message.id)
        return True

    async def purge_cache(self, seconds_since_update: int = 30 * 60, *, dry_run: bool = False,
                          update_items: bool = True) -> int:
        check_ts = (datetime.utcnow() - timedelta(seconds=seconds_since_update)).timestamp()
        check_ts = datetime.fromtimestamp(check_ts)
        cache_copy = self._cache.copy()
        purged = 0
        for item in cache_copy:
            item = cache_copy[item]
            if item.last_update < check_ts:
                if not dry_run and update_items:
                    await self.remove_from_cache(item.message)
                purged += 1
        return purged

    ###############################
    #   Messages

    @property
    def message_cache(self):
        return list(self._cache.values())

    async def get_message(self, *, message: discord.Message = None, message_id: int = None,
                          channel: discord.TextChannel = None, auto_create: bool = False,
                          cache_only: bool = False) -> Optional[StarboardMessage]:
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
                channel = self.bot.get_channel(data.get("channel_id", None))
                if channel is None:
                    return None

            try:
                message = await channel.get_message(message_id)
            except discord.HTTPException:
                return None

        if message is not None:
            if message.id not in self._cache:
                star = StarboardMessage(self, message)
                await star.load_data(auto_create=auto_create)
                self._cache[message.id] = star
            return self._cache[message.id]
        return None

    ###############################
    #   Ignores

    def is_ignored(self, obj: Union[discord.TextChannel, discord.Member]) -> bool:
        if isinstance(obj, discord.Member):
            if obj.bot:  # implicitly block bots from using the starboard
                return True
            return obj.id in self._settings["ignored"]["members"]
        return obj.id in self._settings["ignored"]["channels"] or obj == self.channel

    def ignore(self, obj: Union[discord.TextChannel, discord.Member]):
        if self.is_ignored(obj):
            return False
        ignore_type = "members" if isinstance(obj, discord.Member) else "channels"
        self._settings["ignored"][ignore_type].append(obj.id)
        self._settings_changed = True
        return True

    def unignore(self, obj: Union[discord.TextChannel, discord.Member]):
        if not self.is_ignored(obj):
            return False
        ignore_type = "members" if isinstance(obj, discord.Member) else "channels"
        self._settings["ignored"][ignore_type].remove(obj.id)
        self._settings_changed = True
        return True
