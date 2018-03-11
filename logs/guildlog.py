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
        log_channel = self.log_channel(group.name)
        log_func = getattr(group, str(log_type), lambda **k_args: None)

        try:
            embed: LogEntry = log_func(**kwargs)
            if asyncio.iscoroutine(embed):
                # noinspection PyUnresolvedReferences
                embed = await embed
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
        if self.settings.get("ignored", False):
            return True

        deleted = kwargs.get("deleted", None)
        created = kwargs.get("created", None)
        before = kwargs.get("before", None)
        after = kwargs.get("after", None)
        member = kwargs.get("member", None)  # this is given in voice state events

        if deleted and await self._check(deleted):
            return True
        elif created and await self._check(created):
            return True
        elif before and await self._check(before):
            return True
        elif after and await self._check(after):
            return True
        elif member and await self._check(member):
            return True
        else:
            return False

    def log_channel(self, group: str) -> Optional[discord.TextChannel]:
        return self.bot.get_channel(self.settings["log_channels"].get(group))

    async def _check(self, obj: Union[discord.Member, discord.TextChannel, discord.VoiceChannel,
                                      discord.VoiceState, discord.Message, None]) -> bool:
        if obj is None:
            return False
        if isinstance(obj, discord.Member):
            if obj.bot:
                return True
            if await self.config.member(obj).ignored():
                return True
        elif isinstance(obj, discord.TextChannel) or isinstance(obj, discord.VoiceChannel):
            # noinspection PyTypeChecker
            if await self.config.channel(obj).ignored():
                return True
        elif isinstance(obj, discord.Message):
            if await self.config.channel(obj.channel).ignored() or await self.config.member(obj.author).ignored():
                return True
        elif isinstance(obj, discord.VoiceState) and obj.channel:
            if await self.config.channel(obj.channel).ignored():
                return True
        return False
