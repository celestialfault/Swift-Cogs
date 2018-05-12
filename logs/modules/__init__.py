from typing import Dict, Type, Union

from logs.core import Module
from logs.modules.channel import ChannelModule
from logs.modules.guild import GuildModule
from logs.modules.member import MemberModule
from logs.modules.message import MessageModule
from logs.modules.role import RoleModule
from logs.modules.voice import VoiceModule

__all__ = ("Module", "modules")

modules = {}  # type: Dict[str, Type[Module]]
default_modules = [VoiceModule, GuildModule, RoleModule, MessageModule, MemberModule, ChannelModule]


def register(module: Type[Module]):
    # noinspection PyTypeChecker
    imodule = module(guild=None)
    if imodule.name in modules:
        modules.pop(imodule.name).unregister()
    module.register()
    modules[imodule.name] = module


def unregister(module: Union[Type[Module], str]):
    module_id = module if not isinstance(module, Module) else module(guild=None).name
    modules.pop(module_id).unregister()
