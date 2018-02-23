import asyncio
import contextlib

from enum import Enum
from typing import Optional, Dict

import discord
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.config import Group

from logs import types
from logs.logentry import LogEntry
from logs.utils import find_check


class LogType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

    def __str__(self):
        return self.value


class GuildLog:
    def __init__(self, guild: discord.Guild, bot: Red, config: Config):
        self.guild = guild
        self.bot = bot
        self._config = config
        self.settings = None
        self._formatter = None
        self._logs: Dict[str, types.BaseLog] = {x.name: x(self) for x in types.iterable}

    @property
    def config(self) -> Group:
        return self._config.guild(self.guild)

    async def log(self, group: str, log_type: LogType, **kwargs) -> None:
        """Attempt to log an action.

        Parameters
        -----------
        group: str
            The log group. This should match a log type class in `logs.types`
        log_type: LogType
            The log action type

        Returns
        --------
        None
        """
        if await self.is_ignored(*await find_check(guildlog=self, **kwargs)):
            return

        group = self._logs.get(group)
        log_channel = group.channel()

        # This is probably a terrible idea, but what's the worst that could possibly happen??
        log_func = getattr(group, str(log_type), lambda *args, **k_args: None)

        with contextlib.suppress(NotImplementedError):
            if asyncio.iscoroutinefunction(log_func):
                data: LogEntry = await log_func(**kwargs)
            else:
                data: LogEntry = log_func(**kwargs)

            if data in (None, NotImplemented):
                return

            embed = data.format()
            if embed is None:
                return
            await log_channel.send(embed=embed)

    async def reload_settings(self) -> None:
        """Reloads the settings for this GuildLog instance"""
        self.settings = await self.config.all()

    async def is_ignored(self, *checks):
        if self.settings["ignored"]:
            return True
        if checks:
            for obj in checks:
                if obj is None:
                    continue
                if isinstance(obj, discord.Member):
                    if obj.bot:
                        return True
                    if await self._config.member(obj).ignored():
                        return True
                elif isinstance(obj, discord.TextChannel) or isinstance(obj, discord.VoiceChannel):
                    # noinspection PyTypeChecker
                    if await self._config.channel(obj).ignored():
                        return True
        return False

    def log_channel(self, group: str) -> Optional[discord.TextChannel]:
        return self.bot.get_channel(self.settings["log_channels"].get(group))

    async def init(self):
        if self.settings is not None:
            return
        self.settings = await self.config.all()
