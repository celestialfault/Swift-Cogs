from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any

import asyncio

import discord

from redbot.core.config import Group

from starboard.starboardmessage import StarboardMessage
from starboard.base import StarboardBase
from starboard.log import log

from cog_shared.odinair_libs import IterQueue

__all__ = ('StarboardGuild',)


class StarboardGuild(StarboardBase):
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.update_queue = IterQueue()

        self._migration_lock = asyncio.Lock()
        self._cache = {}  # type: Dict[int, StarboardMessage]
        self._settings = None  # type: Dict[str, Any]

    def __repr__(self):
        return "<GuildStarboard guild={0!r} cache_size={1}>".format(self.guild, len(self._cache))

    async def init(self):
        log.debug("Initializing guild {}".format(self.guild.id))
        await self.reload_settings()

    async def reload_settings(self):
        self._settings = await self.config.guild(self.guild).all()

    @property
    def guild_config(self) -> Group:
        return self.config.guild(self.guild)

    @property
    def messages(self) -> Group:
        return self.config.custom("MESSAGES", self.guild.id)

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

    async def starboard_channel(self, channel: Optional[discord.TextChannel]=False) -> Optional[discord.TextChannel]:
        if channel is not False:
            if channel and channel.guild.id != self.guild.id:
                raise ValueError("The passed TextChannel is not in the current Guild")
            self._settings["channel"] = getattr(channel, "id", None)
            await self.guild_config.channel.set(getattr(channel, "id", None))
            await self.bot.get_cog("Starboard").create_janitor(self.guild, overwrite=False)
        return self.bot.get_channel(self._settings["channel"])

    async def requirerole(self, toggle: bool = None) -> bool:
        if toggle is not None:
            toggle = bool(toggle)
            await self.guild_config.requirerole.set(toggle)
            self._settings["requirerole"] = toggle
        return self._settings["requirerole"]

    async def selfstar(self, toggle: bool = None) -> bool:
        if toggle is not None:
            toggle = bool(toggle)
            await self.guild_config.selfstar.set(toggle)
            self._settings["selfstar"] = toggle
        return self._settings["selfstar"]

    async def min_stars(self, amount: int = None) -> Optional[int]:
        if amount is not None:
            if amount < 1:
                raise ValueError("Amount must be at least one or greater")
            await self.guild_config.min_stars.set(amount)
            self._settings["min_stars"] = amount
        return self._settings["min_stars"]

    async def is_ignored(self, obj: Union[discord.TextChannel, discord.Member], *, check_reqrole: bool = False) -> bool:
        if isinstance(obj, discord.Member):
            if obj.bot:  # implicitly block bots from using the starboard
                return True
            require_role = self.bot.get_cog("RequireRole")
            if require_role:
                if self._settings["requirerole"] and not await require_role.check(obj) and check_reqrole:
                    return True
            return obj.id in self._settings["ignored"]["members"]
        return obj.id in self._settings["ignored"]["channels"] or obj.id == getattr(await self.starboard_channel(),
                                                                                    "id", None)

    async def _append_list(self, *fields: str, value):
        c = self.guild_config
        for field in fields:
            c = c.get_attr(field)
        async with c() as lst:
            if value in lst:
                return
            lst.append(value)
        await self.reload_settings()

    async def _rm_list(self, *fields: str, value):
        c = self.guild_config
        for field in fields:
            c = c.get_attr(field)
        async with c() as lst:
            if value in lst:
                return
            lst.remove(value)
        await self.reload_settings()

    async def ignore(self, obj: Union[discord.TextChannel, discord.Member]):
        if await self.is_ignored(obj, check_reqrole=False):
            return False
        if isinstance(obj, discord.TextChannel):
            await self._append_list("ignored", "channels", value=obj.id)
            return True
        if isinstance(obj, discord.Member):
            await self._append_list("ignored", "members", value=obj.id)
            return True
        return False

    async def unignore(self, obj: Union[discord.TextChannel, discord.Member]):
        if not await self.is_ignored(obj, check_reqrole=False):
            return False
        if isinstance(obj, discord.TextChannel):
            await self._rm_list("ignored", "channels", value=obj.id)
            return True
        if isinstance(obj, discord.Member):
            await self._rm_list("ignored", "members", value=obj.id)
            return True
        return False
