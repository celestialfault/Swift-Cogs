import logging
import re
from abc import ABC, abstractmethod
from keyword import iskeyword
from typing import Dict, Iterable, Optional, Tuple, Union

import discord
from aiohttp import ClientSession
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.config import Group, Value

from cog_shared.swift_libs import flatten
from logs.core.i18n import i18n
from logs.core.logentry import LogEntry
from logs.core.utils import add_descriptions, replace_dict_items
from logs.core.config import config

log = logging.getLogger("red.odinair.logs")


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


bot = None  # type: Red
session = None  # type: ClientSession
loaded = False


def load(red: Red):
    from logs import modules

    global loaded
    global bot
    global session

    loaded = True
    bot = red
    session = ClientSession()

    for mod in modules.default_modules:
        modules.register(mod)


def unload():
    from logs import modules

    for module in list(modules.modules.values()):
        modules.unregister(module)

    global loaded
    global bot
    global session

    loaded = False
    session.close()
    bot = None
    session = None


# noinspection PyTypeChecker
class Module(ABC):
    """Base logging module class

    Loggers should extend this class with the abstract properties implemented.
    """

    @property
    def bot(self) -> Red:
        assert loaded is True
        return bot

    @property
    def config(self) -> Config:
        assert loaded is True
        return config

    @property
    def session(self) -> ClientSession:
        assert loaded is True
        return session

    _TOGGLE_REGEX = re.compile("(?P<KEY>([a-z0-9]:?)+)=?(?P<VALUE>[a-z]+)?", re.IGNORECASE)

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

    # noinspection PyMethodMayBeStatic
    async def can_modify_settings(self, member: discord.Member):
        """Return a boolean value if the given member can change the current module's settings"""
        return member.guild.owner == member or member.guild_permissions.administrator

    async def is_opt_enabled(self, *opts: str):
        return await self.get_config_value(*opts)()

    def get_config_value(self, *opts: str, guild: bool = False) -> Value:
        _opt = getattr(self, "module_config" if not guild else "guild_config")
        for opt in opts:
            _opt = _opt.get_attr(opt)
        return _opt

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

    async def log_destination(self) -> Optional[Union[discord.TextChannel, discord.Webhook]]:
        """Retrieve the log channel or webhook that should be used for logging the current module"""
        webhook = await self.get_config_value("_webhook")()
        channel_id = await self.get_config_value("_log_channel")()
        if webhook:
            return discord.Webhook.from_url(webhook, adapter=discord.AsyncWebhookAdapter(session))
        return self.bot.get_channel(channel_id)

    async def set_destination(
        self, destination: Union[discord.TextChannel, discord.Webhook] = None
    ):
        if destination is None:
            await self.get_config_value("_log_channel").set(None)
            await self.get_config_value("_webhook").set(None)
        elif isinstance(destination, discord.Webhook):
            pass

    def icon_uri(self, member: discord.Member = None):
        """Helper function for embed icon_url fields"""
        if member is None:
            if self.is_global:
                return self.bot.user.avatar_url_as(format="png")
            return self.guild.icon_url_as(format="png")
        return member.avatar_url_as(format="png")

    async def toggle_options(self, *opts: str):
        """Toggle config options

        `opts` should be a set of str values, similar to `opt1:opt2`, with the ability
        to specify boolean values by appending `=<bool>`, such as `opt1:opt2=true`.
        """
        keys = {}  # type: Dict[Tuple[str, ...], Optional[bool]]
        for x in opts:
            # This could probably be done in a better way without regex, but this was
            # the cleaner method as opposed to heavily using .split(s)[i]
            match = self._TOGGLE_REGEX.match(x)
            val = match.group("VALUE")
            if val is not None:
                val = val in ("true", "on")
            keys[tuple(match.group("KEY").split(":"))] = val

        for key, val in keys.items():
            opt = self.get_config_value(*key)
            if isinstance(opt, Group):
                continue

            if val is None:
                val = not await opt()

            await opt.set(val)

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
        if isinstance(log_destination, discord.Webhook):
            dest = i18n("Logging via webhook")
        elif isinstance(log_destination, discord.TextChannel):
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
        ValueError
            Raised if `fn_name` is not a valid function name
        discord.HTTPException
            An HTTP exception was encountered while trying to send the log.
            Currently only 400 Bad Request exceptions are raised,
            and all other exceptions are swallowed.
        """
        # chances are, if someone's trying to call a parser function with an invalid name,
        # they've either mucked up their log() call, or the module
        # would raise a SyntaxError when trying to load it regardless
        if not fn_name.isidentifier() or iskeyword(fn_name):
            raise ValueError("fn_name is not a valid identifier")

        dest = await self.log_destination()
        if dest is None or await self.is_ignored(*args, **kwargs):
            return

        fn = getattr(self, fn_name)
        data = await discord.utils.maybe_coroutine(
            fn, *args, **kwargs
        )  # type: Union[LogEntry, Iterable]
        if not isinstance(data, Iterable):
            data = [data]  # type: Iterable[LogEntry]

        for embed in data:
            if not embed:
                continue
            try:
                kwargs = {
                    "avatar_url": self.bot.user.avatar_url_as(format="png"),
                    "username": self.bot.user.name,
                } if isinstance(
                    dest, discord.Webhook
                ) else {}
                await embed.send(dest, **kwargs)
            except discord.HTTPException as e:
                if e.status == 400:
                    # don't ignore bad request exceptions, as this can indicate
                    # that something was overlooked or improperly done by the parser function
                    raise

                if (
                    isinstance(dest, discord.Webhook)
                    and isinstance(e, (discord.Forbidden, discord.NotFound))
                ):
                    log.warning(
                        (
                            "Clearing errored webhook for guild {self.guild.id} "
                            "{self.name} module"
                        ).format(
                            self=self
                        )
                    )
                    await self.get_config_value("_webhook").set(None)
                elif isinstance(e, discord.Forbidden):
                    log.warning(
                        "Encountered forbidden error while logging result of "
                        "{}.{} to {}: {}".format(self.__class__.__name__, fn_name, dest, e.text)
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
