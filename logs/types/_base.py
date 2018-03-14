import discord
from abc import ABCMeta, abstractmethod
from typing import Dict


class BaseLog(metaclass=ABCMeta):
    """Log type common base"""
    def __init__(self, guild):
        from logs.guildlog import GuildLog
        self.guild: GuildLog = guild

    def __str__(self):
        return self.name

    # Helper methods for subclasses

    @property
    def guild_icon_url(self):
        return self.guild.guild.icon_url

    def icon_url(self, member: discord.Member = None):
        return getattr(member, "avatar_url_as", lambda **kwargs: self.guild_icon_url)(format="png")

    @property
    def settings(self) -> Dict[str, bool]:
        return self.guild.settings.get(self.name, {})

    def is_enabled(self, setting: str) -> bool:
        return self.settings.get(setting, False)

    def is_disabled(self, setting: str) -> bool:
        return not self.is_enabled(setting)

    def has_changed(self, before, after, setting: str):
        return before != after and self.is_enabled(setting)

    # Abstract attributes that subclasses are expected to implement

    @property
    @abstractmethod
    def name(self) -> str:
        return NotImplemented

    @property
    @abstractmethod
    def descriptions(self) -> Dict[str, str]:
        return {}

    @abstractmethod
    async def create(self, created, **kwargs):
        return NotImplemented

    @abstractmethod
    async def update(self, before, after, **kwargs):
        return NotImplemented

    @abstractmethod
    async def delete(self, deleted, **kwargs):
        return NotImplemented
