from typing import Dict, Type
from logs.core import Module

from .voice import VoiceModule
from .guild import GuildModule
from .role import RoleModule
from .message import MessageModule
from .member import MemberModule
from .channel import ChannelModule

__all__ = (
    "Module",
    "VoiceModule",
    "GuildModule",
    "RoleModule",
    "MessageModule",
    "MemberModule",
    "ChannelModule",
    "all_modules",
)

all_modules = {
    "voice": VoiceModule,
    "guild": GuildModule,
    "role": RoleModule,
    "message": MessageModule,
    "member": MemberModule,
    "channel": ChannelModule,
}  # type: Dict[str, Type[Module]]
