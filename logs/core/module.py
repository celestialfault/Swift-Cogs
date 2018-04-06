from abc import ABC, abstractmethod
from typing import Iterable, Optional, Union, Tuple, Dict
from aiohttp import ClientSession

import discord

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.config import Group, Value

from logs.core.logentry import LogEntry
from logs.core.i18n import _
from logs.core.utils import add_descriptions, replace_dict_items

from cog_shared.odinair_libs.formatting import flatten

_module_cache = {}
_guild_ignores = {}


def get_module_cache(guild: discord.Guild = None):
    if guild:
        return _module_cache.get(guild.id, {})
    return _module_cache


def get_ignores(guild: discord.Guild) -> Dict[str, Iterable[int]]:
    return _guild_ignores.get(guild.id, {})


async def load_ignores(guild: discord.Guild):
    _guild_ignores[guild.id] = await Module.config.guild(guild).ignore.all()


async def reload_guild_modules(guild: discord.Guild):
    await load_ignores(guild)
    for module in get_module_cache(guild):
        if isinstance(module, str):
            module = get_module_cache(guild)[module]
        await module.reload_settings()


async def get_module(module_id: str, guild: discord.Guild, *args, **kwargs):
    from logs.modules import all_modules
    await load_ignores(guild)
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


class Module(ABC):
    """Base logging module class

    Loggers should extend this class with the abstract properties implemented.
    """
    # the following attributes are populated upon cog initialization
    config: Config = None
    bot: Red = None
    session: ClientSession = None

    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.module_settings = {}

    async def init_module(self):
        """Helper method to allow modules to have their own init procedures"""
        await self.reload_settings()

    @property
    @abstractmethod
    def name(self) -> str:
        """Internal name used for module config storage"""
        raise NotImplementedError

    @property
    @abstractmethod
    def friendly_name(self):
        """Friendly name that is shown to end-users"""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of the module that is shown to end-users"""
        raise NotImplementedError

    @property
    @abstractmethod
    def settings(self) -> dict:
        """Descriptions of the module's config settings"""
        raise NotImplementedError

    @property
    def opt_keys(self) -> Iterable[str]:
        """Available config option keys. Sub-dicts are denoted by `:` separator characters."""
        return list(flatten(self.defaults, sep=":"))

    @property
    def defaults(self) -> dict:
        """Default config values"""
        return replace_dict_items(self.settings, False)

    @property
    def descriptions(self):
        return {
            "module": self.description,
            "options": flatten(self.settings, sep=":")
        }

    def has_changed(self, *items, conf_setting: Tuple[str, ...] = None):
        changed = False
        for item in items:
            for compare in items:
                if item != compare:
                    changed = True
                    break
        return changed and (self.is_opt_enabled(*conf_setting) if conf_setting else True)

    def is_opt_enabled(self, *opts: str):
        return self.get_config_value(*opts)

    def is_opt_disabled(self, *opts: str):
        return not self.is_opt_enabled(*opts)

    def get_config_value(self, *opts: str, config_value: bool = False, guild: bool = False) -> Value:
        config_value = config_value if guild is False else True
        if config_value:
            _opt = getattr(self, "module_config" if not guild else "guild_config")
        else:
            _opt = self.module_settings
        for opt in opts:
            if config_value is False:
                _opt = _opt[opt]
            else:
                _opt = _opt.get_attr(opt)
        return _opt

    @property
    def module_config(self) -> Group:
        """Retrieve the current guilds module config group"""
        return self.guild_config.get_attr(self.name)

    @property
    def guild_config(self):
        """Retrieve the current guilds scoped config group"""
        return self.config.guild(self.guild)

    async def reload_settings(self):
        self.module_settings = await self.config.guild(self.guild).get_attr(self.name).all()

    @property
    def log_to(self) -> Optional[Union[discord.TextChannel, discord.Webhook]]:
        """Retrieve the log channel or webhook that should be used for logging with the current module"""
        webhook = self.module_settings.get("_webhook", None)
        channel_id = self.module_settings.get("_log_channel", None)
        if webhook:
            return discord.Webhook.from_url(webhook, adapter=discord.AsyncWebhookAdapter(self.session))
        return self.bot.get_channel(channel_id)

    def icon_uri(self, member: discord.Member = None):
        """Helper function for embed icon_url fields"""
        if member is None:
            return self.guild.icon_url_as(format="png")
        return member.avatar_url_as(format="png")

    async def toggle_options(self, *opts: str):
        """Toggle config options"""
        for opt in opts:
            opt = opt.replace(" ", "")
            if not "".join(opt.split("=")[0].split(":")).rstrip():
                continue

            # Split on '=' characters; this allows for syntax like 'config:val=true'
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

        await self.reload_settings()
        return await self.module_config.all()

    def config_embed(self):
        module_opts = {x: y for x, y in flatten(self.module_settings, sep=":").items() if x in self.opt_keys}

        enabled = add_descriptions([x for x in module_opts if module_opts[x]], self.descriptions["options"])
        disabled = add_descriptions([x for x in module_opts if not module_opts[x]], self.descriptions["options"])

        dest = _("Disabled")
        if isinstance(self.log_to, discord.Webhook):
            dest = _("Webhook")
        elif isinstance(self.log_to, discord.TextChannel):
            dest = _("Channel {}").format(self.log_to.mention)

        embed = discord.Embed(colour=discord.Colour.blurple(), description=self.descriptions["module"])
        embed.add_field(name=_("Logging"), value=dest, inline=False)
        embed.set_author(name=_("{} module settings").format(self.friendly_name), icon_url=self.icon_uri())
        embed.add_field(name=_("Enabled"),
                        value=enabled or _("**None** \N{EM DASH} All of this module's options are disabled"),
                        inline=False)
        embed.add_field(name=_("Disabled"),
                        value=disabled or _("**None** \N{EM DASH} All of this module's options are enabled"),
                        inline=False)
        return embed

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
        return get_ignores(self.guild).get("guild", False) or any([self._check(x) for x in args])

    def _check(self, item) -> bool:
        channels = get_ignores(self.guild).get("channels", {})
        roles = get_ignores(self.guild).get("roles", {})
        members = get_ignores(self.guild).get("members", {})
        member_roles = get_ignores(self.guild).get("member_roles", {})

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
