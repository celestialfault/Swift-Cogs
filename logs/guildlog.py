import asyncio

from enum import Enum
from typing import Optional, Union

import discord
from redbot.core import Config
from redbot.core.bot import Red

from logs.logentry import LogFormat
from logs.utils import extract_check, find_check


def setup(_bot: Red, _config: Config):
    global bot
    bot = _bot
    global config
    config = _config


class LogType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

    def __str__(self):
        return self.value


class GuildLog:
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.bot = bot
        self._formatter = None
        self.config = config.guild(self.guild)

    async def log(self, group, log_type: LogType, **kwargs):
        check = extract_check(find_check(**kwargs))
        if isinstance(check, discord.Member) and check.bot:
            return
        elif await self.is_ignored(check):
            return
        group = group(self)
        log_type = str(log_type)
        log_func = getattr(group, log_type, None)
        if log_func is None:
            return
        log_channel = await self.log_channel(group.name)
        if log_channel is None:
            return
        try:
            data = await log_func(**kwargs) if asyncio.iscoroutinefunction(log_func) else log_func(**kwargs)
        except (NotImplementedError, KeyError):  # Silently swallow NotImplementedError and KeyError exceptions
            return
        else:
            if data is None:
                return
            # TypeError: Event parser was expected to return LogEntry, instead got LogEntry
            # ?????????????????????????????
            if getattr(data, "add_field", None) is None and getattr(data, "format", None) is None:
                raise TypeError("Event parser was expected to return LogEntry, instead got %s" %
                                data.__class__.__name__)
            data = data.format(LogFormat(await self.config.format()))
            if data is None:
                return
            try:
                if isinstance(data, discord.Embed):
                    await log_channel.send(embed=data)
                else:
                    await log_channel.send(data)
            except (discord.Forbidden, discord.HTTPException):
                pass

    async def log_channel(self, group: str) -> Optional[discord.TextChannel]:
        channel_id = await self.config.log_channels.get_attr(group)
        if channel_id is None:
            return None
        return self.bot.get_channel(channel_id)

    async def is_ignored(self, check: Union[discord.Member, discord.TextChannel]=None):
        if await self.config.ignored():
            return True

        if check is None:
            return False

        if isinstance(check, discord.Member):
            return await config.member(check).ignored()
        elif isinstance(check, discord.TextChannel) or isinstance(check, discord.VoiceChannel):
            # noinspection PyTypeChecker
            return await config.channel(check).ignored()
        else:
            return False
