import discord
from abc import ABC

from typing import Dict, Optional


class BaseLog(ABC):
    """Log type common base"""
    name: str = NotImplemented
    descriptions: Dict[str, str] = {}

    # noinspection PyUnusedLocal
    def __init__(self, guild, **kwargs):
        from logs.guildlog import GuildLog
        self.guild: GuildLog = guild

    def __str__(self):
        return self.name

    def channel(self) -> Optional[discord.TextChannel]:
        return self.guild.bot.get_channel(self.guild.settings["log_channels"].get(self.name))

    @property
    def settings(self) -> Dict[str, bool]:
        return self.guild.settings.get(self.name, {})

    async def create(self, created, **kwargs):
        return NotImplemented

    async def update(self, before, after, **kwargs):
        return NotImplemented

    async def delete(self, deleted, **kwargs):
        return NotImplemented
