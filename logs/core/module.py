from abc import ABCMeta, abstractmethod
from typing import Iterable, Optional, Dict, Any, Union, List
from aiohttp import ClientSession

import discord

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.config import Group, Value

from logs.core import LogEntry

from cog_shared.odinair_libs.formatting import flatten

_module_cache = {}


def get_module_cache(guild: discord.Guild = None):
    if guild:
        return _module_cache.get(guild.id, {})
    return _module_cache


async def reload_guild_modules(guild: discord.Guild):
    for module in get_module_cache(guild):
        if isinstance(module, str):
            module = get_module_cache(guild)[module]
        await module.reload_settings()


async def get_module(module_id: str, guild: discord.Guild, *args, **kwargs):
    from logs.modules import all_modules
    module_id = module_id.lower()
    if guild.id not in _module_cache:
        _module_cache[guild.id] = {}
    if module_id in _module_cache[guild.id]:
        return _module_cache[guild.id][module_id]
    if module_id in all_modules:
        module = all_modules[module_id](guild, *args, **kwargs)
        _module_cache[guild.id][module_id] = module
        await module.init_module()
        return module
    raise RuntimeError(f"a module with the id {module_id} was not found")


class Module(metaclass=ABCMeta):
    # the following attributes are populated upon cog initialization
    config: Config = None
    bot: Red = None
    session: ClientSession = None

    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.settings: Dict[str, ...] = {}
        self.ignore: Dict[str, List[int]] = {}

    async def init_module(self):
        await self.reload_settings()

    async def reload_settings(self):
        self.settings = await self.config.guild(self.guild).get_attr(self.name).all()
        self.ignore = await self.config.guild(self.guild).ignore.all()

    # Begin abstract methods

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

    # End abstract methods
    # Begin helper methods

    @property
    def opt_keys(self) -> Iterable[str]:
        return list(flatten(self.defaults, sep=":"))

    def is_opt_enabled(self, *opts: str):
        return self.get_config_value(*opts)

    def is_opt_disabled(self, *opts: str):
        return not self.is_opt_enabled(*opts)

    def get_config_value(self, *opts: str, config_value: bool = False, guild: bool = False) -> Value:
        config_value = config_value if guild is False else True
        if config_value:
            _opt = getattr(self, "module_config" if not guild else "guild_config")
        else:
            _opt = self.settings
        for opt in opts:
            if config_value is False:
                _opt = _opt[opt]
            else:
                _opt = _opt.get_attr(opt)
        return _opt

    # The following methods are used by external code, and as such they shouldn't be modified by subclasses

    @property
    def module_config(self) -> Group:
        return self.guild_config.get_attr(self.name)

    @property
    def guild_config(self):
        return self.config.guild(self.guild)

    @property
    def log_to(self) -> Optional[Union[discord.TextChannel, discord.Webhook]]:
        webhook = self.settings.get("_webhook", None)
        channel_id = self.settings.get("_log_channel", None)
        if webhook:
            return discord.Webhook.from_url(webhook, adapter=discord.AsyncWebhookAdapter(self.session))
        return self.bot.get_channel(channel_id)

    def icon_uri(self, member: discord.Member = None):
        if member is None:
            return self.guild.icon_url_as(format="png")
        return member.avatar_url_as(format="png")

    async def toggle_options(self, *opts: str):
        for opt in opts:
            if not "".join(opt.split(":")):
                continue

            # I'm so sorry for this monstrosity
            _opts = opt.split("=")
            opt_split = _opts[0].split(":")
            opt = self.get_config_value(*opt_split, config_value=True)
            if isinstance(opt, Group):
                continue

            if len(_opts) > 1:
                new_val = True if _opts[1].lower() in ('yes', 'true', '1', 'on') else False
            else:
                new_val = not await opt()
            await opt.set(new_val)

        return await self.module_config.all()

    async def log(self, fn_name: str, *args, **kwargs):
        if self.log_to is None or self.is_ignored(*args, **kwargs):
            return
        fn = getattr(self, fn_name)
        data: Union[LogEntry, Iterable] = await discord.utils.maybe_coroutine(fn, *args, **kwargs)
        if not isinstance(data, Iterable):
            data: Iterable[LogEntry] = [data]

        kwargs = {
            "avatar_url": self.bot.user.avatar_url_as(format="png"),
            "username": self.bot.user.name
        } if isinstance(self.log_to, discord.Webhook) else {}

        for embed in data:
            if not embed:
                continue
            try:
                await embed.send(self.log_to, **kwargs)
            except discord.HTTPException as e:
                if e.status == 400 or isinstance(e, discord.Forbidden):
                    raise

    def is_ignored(self, *args, **kwargs) -> bool:
        kwargs = tuple(y for x, y in tuple(kwargs))
        args = args + kwargs
        return self.ignore.get("guild", False) or any([self._check(x) for x in args])

    def _check(self, item) -> bool:
        channels = self.ignore.get("channels", {})
        roles = self.ignore.get("roles", {})
        members = self.ignore.get("members", {})
        member_roles = self.ignore.get("member_roles", {})

        if isinstance(item, discord.Member):
            return any([item.bot, item.id in members, *[x.id in member_roles for x in item.roles]])
        elif isinstance(item, discord.abc.GuildChannel):
            return any([item.id in channels, getattr(item.category, "id", None) in channels])
        elif isinstance(item, discord.Role):
            return item.id in roles
        elif isinstance(item, discord.VoiceState):
            return getattr(item.channel, "id", None) in channels
        elif isinstance(item, discord.Message):
            return any([self._check(item.author), self._check(item.channel)])

        return False

    # End helper methods
