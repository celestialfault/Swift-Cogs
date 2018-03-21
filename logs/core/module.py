import asyncio
from abc import ABCMeta, abstractmethod
from typing import Iterable, Optional, Dict, Any

import discord

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.config import Group, Value

from odinair_libs.formatting import flatten


class Module(metaclass=ABCMeta):
    # the following attributes are populated when the cog is initialized
    config: Config = None
    bot: Red = None

    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.settings: Dict[str, ...] = {}

    async def init_module(self):
        await self.reload_settings()

    async def reload_settings(self):
        self.settings = await self.config.guild(self.guild).get_raw(self.name)

    @classmethod
    async def get_module(cls, module_id: str, *args, **kwargs):
        from logs.modules import all_modules
        module_id = module_id.lower()
        if module_id in all_modules:
            module = all_modules[module_id](*args, **kwargs)
            await module.init_module()
            return module
        return None

    # Abstract methods

    @property
    @abstractmethod
    def friendly_name(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def module_description(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def option_descriptions(self) -> Dict[str, str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def defaults(self) -> Dict[str, Any]:
        raise NotImplementedError

    # Helper methods

    @property
    def opt_keys(self) -> Iterable[str]:
        return list(flatten(self.defaults, sep=":"))

    @property
    def module_config(self) -> Group:
        return self.config.guild(self.guild).get_attr(self.name)

    @property
    def log_channel(self) -> Optional[discord.TextChannel]:
        return self.bot.get_channel(self.settings.get("_log_channel", None))

    def get_config_value(self, *opts: str, config_value: bool = False) -> Value:
        if config_value is False:
            _opt = self.settings
        else:
            _opt = self.module_config
        for opt in opts:
            if config_value is False:
                _opt = _opt[opt]
            else:
                _opt = _opt.get_attr(opt)
        return _opt

    def icon_uri(self, member: discord.Member = None):
        if member is None:
            return self.guild.icon_url_as(format="png")
        return member.avatar_url_as(format="png")

    async def toggle_options(self, *opts: str):
        opts = [x.split(":") for x in opts if "".join(x.split(":"))]
        for opt in opts:
            opt = self.get_config_value(*opt, config_value=True)
            if isinstance(opt, Group):
                continue
            await opt.set(not await opt())
        return await self.module_config.all()

    async def log(self, func_name: str, *args, **kwargs):
        if self.log_channel is None:
            return

        func = getattr(self, func_name)
        try:
            if asyncio.iscoroutinefunction(func):
                data = await func(*args, **kwargs)
            else:
                data = func(*args, **kwargs)
        except NotImplementedError:
            return

        if data is None or data is NotImplemented:
            pass
        elif isinstance(data, list):
            for item in data:
                if not item.is_valid:
                    continue
                await self.log_channel.send(embed=item)
        else:  # assume LogEntry
            if not data.is_valid:
                return
            await self.log_channel.send(embed=data)

    def is_opt_enabled(self, *opts: str):
        return self.get_config_value(*opts)

    def is_opt_disabled(self, *opts: str):
        return not self.is_opt_enabled(*opts)
