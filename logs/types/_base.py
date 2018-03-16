from abc import ABCMeta, abstractmethod
from typing import Dict

import discord

from logs.guildlog import GuildLog
# noinspection PyUnresolvedReferences
from logs.i18n import _


class BaseLogType(metaclass=ABCMeta):
    """Log type common base"""
    def __init__(self, guild: GuildLog):
        self.guild = guild

    def __str__(self):
        return self.name

    @property
    def log_channel_opt(self):
        """Log channel setting name. This may be overridden by subclasses, otherwise this defaults to `name`."""
        return self.name

    # Helper methods for subclasses

    @property
    def guild_icon_url(self):
        """Returns the guild's icon url"""
        return self.guild.guild.icon_url

    def icon_url(self, member: discord.Member = None):
        """Get the guild icon url, or the avatar url for a member"""
        # yes, this is a terrible way to do this, but hey - it at least works
        return getattr(member, "avatar_url_as", lambda **kwargs: self.guild_icon_url)(format="png")

    @property
    def settings(self) -> Dict[str, bool]:
        """Get this log types guild settings"""
        return self.guild.settings.get(self.name, {})

    def is_enabled(self, setting: str) -> bool:
        """Check if `setting` is enabled"""
        return self.settings.get(setting, False)

    def is_disabled(self, setting: str) -> bool:
        """Alias for `not <BaseLog>.is_enabled(setting)`"""
        return not self.is_enabled(setting)

    def has_changed(self, before, after, setting: str):
        """Check if `before` and `after` are different from each other, and if `setting` is enabled"""
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
