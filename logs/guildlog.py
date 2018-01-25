import asyncio

from enum import Enum
from typing import Optional, Union

import discord
from redbot.core import Config
from redbot.core.bot import Red

from logs.logentry import LogFormat, LogEntry
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
        check = await find_check(guildlog=self, **kwargs)
        if await self.is_ignored(check):
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
        except NotImplementedError:  # Silently swallow NotImplementedError exceptions
            return
        else:
            if data is None:
                return
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

    async def is_ignored(self, checks=None):
        if await self.config.ignored():
            return True
        if checks:
            for item in checks:
                if item is None:
                    continue
                if isinstance(item, discord.Member):
                    if item.bot:
                        return True
                    if await config.member(item).ignored():
                        return True
                elif isinstance(checks, discord.TextChannel) or isinstance(checks, discord.VoiceChannel):
                    if await config.channel(item).ignored():
                        return True
        return False
