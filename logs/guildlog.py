import asyncio

from enum import Enum
from typing import Optional, Dict, Union

import discord

from redbot.core.config import Group

from logs import types
from logs.logentry import LogEntry

__all__ = ['LogType', 'GuildLog']


class LogType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

    def __str__(self):
        return self.value


class GuildLog:
    def __init__(self, guild: discord.Guild, cog):
        if not isinstance(guild, discord.Guild):
            raise TypeError(f'expected guild to be of type discord.Guild, received {guild.__class__.__name__}')
        self.guild = guild
        self._types: Dict[str, types.BaseLog] = {x.name: x(self) for x in types.iterable}

        from logs.logs import Logs
        self._cog: Logs = cog
        self.bot = self._cog.bot
        self.config = self._cog.config

        self.settings: Dict[str, Union[str, bool, Dict[str, bool]]] = None

    @property
    def guild_config(self) -> Group:
        return self.config.guild(self.guild)

    async def init(self):
        if self.settings is not None:
            return
        self.settings = await self.guild_config.all()

    async def log(self, group: str, log_type: LogType, **kwargs) -> None:
        """Attempt to log an action.

        Parameters
        -----------
        group: str
            The log group. This should match a log type class in `logs.types`
        log_type: LogType
            The log action type
        """
        if await self.is_ignored(**kwargs):
            return

        group = self._types.get(group)
        log_func = getattr(group, str(log_type), lambda **k_args: None)

        log_channel = self.log_channel(group.name)
        if log_channel is None:
            return

        try:
            if asyncio.iscoroutinefunction(log_func):
                embed: LogEntry = await log_func(**kwargs)
            else:
                embed: LogEntry = log_func(**kwargs)
        except NotImplementedError:
            return
        else:
            if embed in (None, NotImplemented) or not embed.is_valid:
                return
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass

    async def reload_settings(self) -> None:
        """Reloads the settings for this GuildLog instance"""
        self.settings = await self.guild_config.all()

    async def is_ignored(self, **kwargs):
        return any([self.settings.get("ignored", False), *[await self._check(kwargs[x]) for x in kwargs]])

    def log_channel(self, group: str) -> Optional[discord.TextChannel]:
        return self.bot.get_channel(self.settings["log_channels"].get(group))

    async def _check(self, check: Union[discord.Member, discord.TextChannel, discord.VoiceChannel,
                                        discord.VoiceState, discord.Message, discord.Role, None]) -> bool:
        if check is None:
            return False

        if isinstance(check, discord.Member):
            return any([check.bot, await self.config.member(check).ignored()])
        elif isinstance(check, discord.Message):
            return any([await self._check(check.author), await self._check(check.channel)])
        elif isinstance(check, discord.TextChannel) or isinstance(check, discord.VoiceChannel):
            # noinspection PyTypeChecker
            return await self.config.channel(check).ignored()
        elif isinstance(check, discord.VoiceState) and check.channel:
            return await self.config.channel(check.channel).ignored()
        elif isinstance(check, discord.Role):
            return await self.config.role(check).ignored()
        return False
