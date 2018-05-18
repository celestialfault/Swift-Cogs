import re
from abc import ABC, abstractmethod
from typing import Iterable, Optional, Union, MutableMapping

import discord
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.config import Group, Value

from cog_shared.swift_libs import flatten, flatten_values
from logs.core.i18n import i18n
from logs.core.logentry import LogEntry
from logs.core.utils import add_descriptions, replace_dict_items
from logs.core.config import config
from logs.core.log import log

bot: Red = None
_TOGGLE_REGEX = re.compile("(?P<KEY>([a-z0-9]:?)+)=?(?P<VALUE>[a-z]+)?", re.IGNORECASE)


def get_module(module_id: str, *args, **kwargs) -> "Module":
    from logs.modules import modules

    return modules[module_id.lower()](*args, **kwargs)


async def log_event(module: str, event: str, *args, use_guild: discord.Guild = None, **kwargs):
    arguments = args + tuple(kwargs.values())
    guild = use_guild
    if guild is None:
        for arg in arguments:
            if isinstance(arg, discord.Guild):
                guild = arg
            else:
                try:
                    guild = getattr(arg, "guild")
                except AttributeError:
                    continue
            break
        if guild is None:
            raise RuntimeError("could not extract a guild object from any of the arguments passed")
    return await get_module(module, guild).log(event, *args, **kwargs)


def load(red: Red):
    from logs import modules

    global bot
    bot = red

    for mod in modules.default_modules:
        modules.register(mod)


def unload():
    from logs import modules

    for module in list(modules.modules.values()):
        modules.unregister(module)

    global bot
    bot = None


# noinspection PyTypeChecker
class Module(ABC):
    """Base logging module class

    Loggers should extend this class with the abstract properties implemented.
    """

    @property
    def bot(self) -> Red:
        return bot

    @property
    def config(self) -> Config:
        return config

    def __init__(self, guild: discord.Guild):
        self.guild = guild

    @classmethod
    def register(cls):
        """Helper method called on module init.

        Can be overridden by subclasses to implement their own setup routine
        """
        pass

    @classmethod
    def unregister(cls):
        """Helper method called when performing unload hooks.

        Can be overridden by subclasses to implement their own cleanup routine
        """
        pass

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
    def is_global(self) -> bool:
        return False

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
        return {"module": self.description, "options": flatten(self.settings, sep=":")}

    @property
    def config_scope(self) -> str:
        return Config.GUILD if not self.is_global else Config.GLOBAL

    @property
    def module_config(self) -> Group:
        """Retrieve the current guilds module config group"""
        return self.root_config.get_attr(self.name)

    @property
    def root_config(self):
        """Retrieve the current guilds scoped config group"""
        if self.is_global is True:
            return self.config
        return self.config.guild(self.guild)

    # noinspection PyMethodMayBeStatic
    async def can_modify_settings(self, member: discord.Member):
        """Return a boolean value if the given member can change the current module's settings"""
        return member.guild.owner == member or member.guild_permissions.administrator

    def get_config_value(self, *opts: str, guild: bool = False) -> Union[Value, Group]:
        _opt = getattr(self, "module_config" if not guild else "guild_config")
        for opt in opts:
            _opt = _opt.get_attr(opt)
        return _opt

    async def is_opt_enabled(self, *opts: str):
        return await self.get_config_value(*opts)()

    async def log_destination(self) -> Optional[discord.TextChannel]:
        """Retrieve the log channel that should be used for logging the current module"""
        return self.bot.get_channel(await self.get_config_value("_log_channel")())

    async def set_destination(self, destination: Optional[discord.TextChannel] = None):
        await self.get_config_value("_log_channel").set(getattr(destination, "id", None))

    def icon_uri(self, member: discord.Member = None):
        """Helper function for embed icon_url fields"""
        if member is None:
            if self.is_global:
                return self.bot.user.avatar_url_as(format="png")
            return self.guild.icon_url_as(format="png")
        return member.avatar_url_as(format="png")

    async def toggle_options(self, *opts: str):
        """User-oriented config option toggle"""
        # The following code consists solely of a series of bad ideas.
        # You're not expected to believe in my development skills
        # while reading this.
        for key, val in {
            tuple(x.group("KEY").split(":")): (
                x.group("VALUE") in ("true", "on", "1", "yes")
                if x.group("VALUE") is not None
                else None
            )
            for opt in opts
            for x in [_TOGGLE_REGEX.match(opt)]
        }.items():
            conf_val = self.get_config_value(*key)
            current_val = await (conf_val.all() if isinstance(conf_val, Group) else conf_val())

            val = (
                (
                    not all(flatten_values(current_val))
                    if isinstance(current_val, MutableMapping)
                    else not current_val
                )
                if val is None
                else val
            )

            if isinstance(current_val, MutableMapping):
                await conf_val.set(replace_dict_items(current_val, val))
            else:
                await conf_val.set(val)

    async def config_embed(self):
        """Get the current module's settings embed"""
        module_opts = {
            x: y
            for x, y in flatten(await self.module_config.all(), sep=":").items()
            if x in self.opt_keys
        }

        enabled = add_descriptions(
            [x for x, y in module_opts.items() if y], self.descriptions["options"]
        )
        disabled = add_descriptions(
            [x for x, y in module_opts.items() if not y], self.descriptions["options"]
        )

        log_destination = await self.log_destination()

        dest = i18n("Logging is disabled")
        if isinstance(log_destination, discord.TextChannel):
            dest = i18n("Logging to channel {channel}").format(channel=log_destination.mention)

        return (
            discord.Embed(
                colour=discord.Colour.blurple(),
                description="{}\n\n{}".format(self.descriptions["module"], dest),
            ).set_author(
                name=i18n("{friendly_name} Logging Module").format(
                    friendly_name=self.friendly_name
                ),
                icon_url=self.icon_uri(),
            ).add_field(
                name=i18n("Enabled"),
                value=enabled
                or i18n("**None** \N{EM DASH} All of this module's options are disabled"),
                inline=False,
            ).add_field(
                name=i18n("Disabled"),
                value=disabled
                or i18n("**None** \N{EM DASH} All of this module's options are enabled"),
                inline=False,
            )
        )

    async def log(self, fn_name: str, *args, **kwargs):
        """Attempt to log an event

        All extra parameters are passed directly to

        Parameters
        -----------
        fn_name: str
            The module parser function to call

        Raises
        -------
        AttributeError
            Raised if no method from the value of `fn_name` exists on the current module
        discord.HTTPException
            An HTTP exception was encountered while trying to send the log event.
            Currently only 400 errors are raised, and all others are swallowed.
        """
        dest = await self.log_destination()
        if dest is None or await self.is_ignored(*args, **kwargs):
            return

        data: Union[LogEntry, Iterable] = await discord.utils.maybe_coroutine(
            getattr(self, fn_name), *args, **kwargs
        )
        if not isinstance(data, Iterable):
            data: Iterable[LogEntry] = [data]

        for embed in data:
            if not embed:
                continue
            try:
                await embed.send(dest)
            except discord.HTTPException as e:
                if e.status in (400,):
                    raise

                if isinstance(e, discord.Forbidden):
                    log.warning(
                        "Encountered forbidden error while logging result of {}.{}: {}".format(
                            self.__class__.__name__, fn_name, dest, e.text
                        )
                    )

    async def is_ignored(self, *args, **kwargs) -> list:
        """Checks if the current guild, or any arguments passed, are set to be ignored from logging.

        Any items that are ignored are returned in a list; any items not ignored are skipped.

        If the current guild is ignored, then only the module's guild is returned,
        and not the items passed.
        """
        args = args + tuple(kwargs.values())
        if not self.is_global and await self.root_config.ignore.guild():
            return [self.guild]

        ignored = []
        for x in args:
            if await self._check(x):
                ignored.append(x)
        return ignored

    async def _check(self, item) -> bool:
        if isinstance(item, discord.Member):
            ignore_roles = await self.root_config.ignore.member_roles()
            return any(
                [
                    item.bot,
                    item.id in await self.root_config.ignore.members(),
                    *[x.id in ignore_roles for x in item.roles],
                ]
            )
        elif isinstance(item, discord.abc.GuildChannel):
            ignore = await self.root_config.ignore.channels()
            # noinspection PyUnresolvedReferences
            return any([item.id in ignore, getattr(item.category, "id", None) in ignore])
        elif isinstance(item, discord.Role):
            return item.id in await self.root_config.ignore.roles()
        elif isinstance(item, discord.VoiceState):
            return getattr(item.channel, "id", None) in await self.root_config.ignore.channels()
        elif isinstance(item, discord.Message):
            return any([await self._check(item.author), await self._check(item.channel)])

        return False
